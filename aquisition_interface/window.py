import pyqtgraph as pg
from PyQt5 import QtGui, QtWidgets

from . import gui


class SMainWindow(QtWidgets.QMainWindow):
    MAX_FREQ = 1e9
    MIN_FREQ = 1.0

    def __init__(self):
        super().__init__()
        self.ui = gui.Ui_MainWindow()
        self.ui.setupUi(self)

        self.ui.raw_img = pg.ImageItem(levels=(0, 1024))
        self.ui.raw_plot = self.ui.raw_window.addPlot(title="Camera image")
        self.ui.raw_plot.addItem(self.ui.raw_img)
        hist = pg.HistogramLUTItem()
        hist.setImageItem(self.ui.raw_img)
        hist.setLevels(0, 1024)
        self.ui.raw_window.addItem(hist)
        self.ui.processed_img = pg.ImageItem(levels=(0, 1024))
        self.ui.processed_plot = self.ui.processed_window.addPlot(title="Camera image")
        self.ui.processed_plot.addItem(self.ui.processed_img)
        hist = pg.HistogramLUTItem()
        hist.setImageItem(self.ui.processed_img)
        hist.setLevels(0, 1024)
        self.ui.processed_window.addItem(hist)

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
