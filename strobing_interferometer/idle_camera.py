import multiprocessing

import numpy as np
import pyqtgraph as pg
import thorlabs_tsi_sdk.tl_camera
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot
from thorlabs_tsi_sdk.tl_camera import TLCameraSDK

from . import gui


class SMainWindow(QtWidgets.QMainWindow):

    exposure_time = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.ui = gui.Ui_MainWindow()
        self.ui.setupUi(self)

        self.ui.raw_img = pg.ImageItem(levels=(0, 1024))
        self.ui.raw_plot = self.ui.raw_window.addPlot(title="Camera image")
        self.ui.raw_plot.getViewBox().setAspectLocked()
        self.ui.raw_plot.addItem(self.ui.raw_img)

        self.ui.exposure_time.valueChanged.connect(self.exposure_time_changed)

    def set_exposure_extrema(self, min_exposure, max_exposure):
        self.ui.exposure_time.setMinimum(min_exposure)
        self.ui.exposure_time.setMaximum(max_exposure)

    def exposure_time_changed(self):
        exp = self.ui.exposure_time.value()
        self.exposure_time.emit(exp)
        # self.ui.freq_select_slider.valueChanged.connect(slider_update)


camera_semaphore = multiprocessing.Event()
camera_lock = multiprocessing.Lock()
is_running = False


class CameraGuiProcess(multiprocessing.Process):
    def __init__(self, camera_sn, **kwargs):
        super().__init__(**kwargs)
        self.camera_sn = camera_sn
        self.stop_event = multiprocessing.Event()

    def run(self):
        self.app = pg.mkQApp("Stroboscopic imaging")

        timer = QtCore.QTimer()

        def stop():
            if self.stop_event.is_set():
                self.app.quit()

        # timer.setSingleShot(True)
        timer.timeout.connect(stop)
        timer.start(5)

        win = SMainWindow()
        win.show()  ## show widget alone in its own window
        win.setWindowTitle("Imaging camera")

        @pyqtSlot(np.ndarray)
        def updateraw(img):
            win.ui.raw_img.setImage(img, autolevels=False)

        @pyqtSlot(int, int)
        def update_exposure_range(exp_min, exp_max):
            win.set_exposure_extrema(
                exp_min,
                exp_max,
            )

        image_acquisition = ImageAcquisition(self.camera_sn)

        image_acquisition.new_frame.connect(updateraw)
        image_acquisition.exposure_range.connect(update_exposure_range)
        win.exposure_time.connect(image_acquisition.change_exposure_time)

        camera_semaphore.set()

        image_acquisition.start()

        self.app.exec()
        camera_semaphore.clear()

        camera_lock.acquire()
        camera_lock.release()
        image_acquisition.quit()

    def stop(self):
        self.stop_event.set()


def run(camera_sn):
    global is_running
    if is_running:
        raise Exception("Gui is already running")
    p = CameraGuiProcess(camera_sn)
    p.start()
    is_running = True
    return p


class ImageAcquisition(QThread):

    new_frame = pyqtSignal(np.ndarray)
    exposure_range = pyqtSignal(int, int)

    def __init__(self, camera_sn, **kwargs):
        super().__init__(**kwargs)
        self.camera_sn = camera_sn
        self.open = False

    @pyqtSlot(int)
    def change_exposure_time(self, exp):
        if self.open:
            self.camera.exposure_time_us = exp

    def init_camera(self):

        camera_lock.acquire()
        try:
            self.sdk = TLCameraSDK()
            self.sdk.discover_available_cameras()
            self.camera = self.sdk.open_camera(self.camera_sn)

            self.exposure_range.emit(
                self.camera.exposure_time_range_us.min,
                self.camera.exposure_time_range_us.max,
            )

            self.camera.image_poll_timeout_ms = 0

            self.camera.frames_per_trigger_zero_for_unlimited = 0
            self.camera.arm(2)
            self.camera.issue_software_trigger()
            self.open = True
        except thorlabs_tsi_sdk.tl_camera.TLCameraError as err:
            print(err)
            self.dispose_camera()
            self.exit()

    def dispose_camera(self):
        try:
            if self.camera is not None:
                self.camera.disarm()
                self.camera.dispose()
            if self.sdk is not None:
                self.sdk.dispose()
        except thorlabs_tsi_sdk.tl_camera.TLCameraError as err:
            print(err)
        finally:
            self.open = False
            camera_lock.release()

    def run(self):
        print("camera init")
        self.camera = None
        self.sdk = None

        timer = QtCore.QTimer()

        def updateData():
            if camera_semaphore.is_set() and self.open:
                try:
                    frame = self.camera.get_pending_frame_or_null()
                    if frame is not None:
                        image = np.copy(frame.image_buffer.T)
                        self.new_frame.emit(image)
                except thorlabs_tsi_sdk.tl_camera.TLCameraError as err:
                    print(err)
                    self.dispose_camera()
                    self.exit()
            elif self.open:
                self.dispose_camera()
            elif camera_semaphore.is_set():
                self.init_camera()

        # timer.setSingleShot(True)
        timer.timeout.connect(updateData)
        timer.start(5)
        self.exec()

        # updateData()
