import logging
import os

import PyQt5
import pyqtgraph as pg
from PyQt5 import QtCore, QtGui, QtWidgets

import gui
from camera import ImageAcquisitionThread
from fake_cam import FakeCam
from processing import StdProcessing

# from thorlabs_tsi_sdk.tl_camera import TLCameraSDK

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

""" Main

When run as a script, a simple Tkinter app is created with just a LiveViewCanvas widget. 

"""


class SMainWindow(QtWidgets.QMainWindow):
    MAX_FREQ = 1e9
    MIN_FREQ = 1.0

    def __init__(self):
        super().__init__()
        self.ui = gui.Ui_MainWindow()
        self.ui.setupUi(self)

        self.ui.raw_img = pg.ImageItem(levels=(0, 1024))
        self.ui.raw_plot = self.ui.raw_imv.addPlot(title="Camera image")
        self.ui.raw_plot.addItem(self.ui.raw_img)
        hist = pg.HistogramLUTItem()
        hist.setImageItem(self.ui.raw_img)
        hist.setLevels(0, 1024)
        self.ui.raw_imv.addItem(hist)
        self.ui.processed_img = pg.ImageItem(levels=(0, 1024))
        self.ui.processed_plot = self.ui.processed_imv.addPlot(title="Camera image")
        self.ui.processed_plot.addItem(self.ui.processed_img)
        hist = pg.HistogramLUTItem()
        hist.setImageItem(self.ui.processed_img)
        hist.setLevels(0, 1024)
        self.ui.processed_imv.addItem(hist)

    def setValidators(self):
        self.ui.freq_field.setValidator(
            QtGui.QDoubleValidator(self.MIN_FREQ, self.MAX_FREQ, 6)
        )
        self.ui.min_freq_field.setValidator(
            QtGui.QDoubleValidator(self.MIN_FREQ, self.MAX_FREQ, 6)
        )
        self.ui.max_freq_field.setValidator(
            QtGui.QDoubleValidator(self.MIN_FREQ, self.MAX_FREQ, 6)
        )

    def setFrequencySelectorLogic(self):
        def slider_update():
            value = self.ui.freq_select_slider.value()
            try:
                min_freq = float(self.ui.min_freq_field.text())
            except ValueError:
                min_freq = self.MIN_FREQ

            try:
                max_freq = float(self.ui.max_freq_field.text())
            except ValueError:
                max_freq = self.MAX_FREQ
            self.ui.freq_field.blockSignals(True)
            self.ui.freq_field.setText(
                str(
                    min_freq
                    + (max_freq - min_freq)
                    * (value - self.ui.freq_select_slider.minimum())
                    / (
                        self.ui.freq_select_slider.maximum()
                        - self.ui.freq_select_slider.minimum()
                    )
                )
            )
            self.ui.freq_field.blockSignals(False)

        self.ui.freq_select_slider.valueChanged.connect(slider_update)

        def freq_update():
            # get all the values and return if failing or put sensible defaults
            try:
                value = float(self.ui.freq_field.text())
            except ValueError:
                return
            try:
                min_freq = float(self.ui.min_freq_field.text())
            except ValueError:
                min_freq = self.MIN_FREQ
            try:
                max_freq = float(self.ui.max_freq_field.text())
            except ValueError:
                max_freq = self.MAX_FREQ
            self.ui.freq_select_slider.blockSignals(True)
            # if out of bounds => move the bounds
            if value < min_freq:
                self.ui.min_freq_field.setText(str(value))
                self.ui.freq_select_slider.setValue(0)
                return
            if value > max_freq:
                self.ui.max_freq_field.setText(str(value))
                self.ui.freq_select_slider.setValue(1000)
                return
            self.ui.freq_select_slider.setValue(
                int(1000 * (value - min_freq) / (max_freq - min_freq))
            )
            self.ui.freq_select_slider.blockSignals(False)

        self.ui.freq_field.editingFinished.connect(freq_update)


if __name__ == "__main__":
    logger.info(f"Hello, my pid is {os.getpid()}")
    # with TLCameraSDK() as sdk:
    #    camera_list = sdk.discover_available_cameras()
    #    with sdk.open_camera(camera_list[0]) as camera:
    camera = FakeCam()
    logger.info("Generating app...")
    image_acquisition_thread = ImageAcquisitionThread(camera)
    processing_thread = StdProcessing(
        image_acquisition_thread.processing_queue, (10, 1024, 1024)
    )
    app = pg.mkQApp("Stroboscopic imaging")
    win = SMainWindow()

    # init window
    win.show()

    win.setValidators()
    win.setFrequencySelectorLogic()

    def update():
        if not image_acquisition_thread.image_queue.empty():
            ts, img = image_acquisition_thread.image_queue.get_nowait()
            win.ui.raw_img.setImage(img, autoLevels=False)
            logger.debug(f"Updated image at timestamp {ts}")
        else:
            logger.debug("Queue empty, not updating")
        if not processing_thread.out_queue.empty():
            ts, img = processing_thread.out_queue.get_nowait()
            win.ui.processed_img.setImage(img)
            logger.debug(f"Updated image at timestamp {ts}")
        else:
            logger.debug("Queue empty, not updating")

    timer = QtCore.QTimer()
    timer.timeout.connect(update)

    logger.info("Setting camera parameters...")
    camera.frames_per_trigger_zero_for_unlimited = 0

    # This buffer size comes from thorlabs' live camera example. Let's keep it
    camera.arm(2)

    timer.start(10)
    camera.issue_software_trigger()

    logger.info("Starting image acquisition")
    processing_thread.start()
    image_acquisition_thread.start()

    logger.info("App starting")
    app.exec()

    logger.info("Waiting for image acquisition thread to finish...")
    processing_thread.stop()
    processing_thread.join()
    image_acquisition_thread.stop()
    image_acquisition_thread.join()

    logger.info("App terminated. Goodbye!")
