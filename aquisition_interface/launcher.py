import logging
import os
import signal
import sys

import numpy as np
import pyqtgraph as pg
from PyQt5 import QtCore

from .camera import ImageAcquisitionThread
from .fake_cam import FakeCam
from .processing import (DemodRecordingQueue, ProcessingProcess,
                         StatRecordingQueue)
from .window import SMainWindow

# from thorlabs_tsi_sdk.tl_camera import TLCameraSDK

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

""" Main
"""


def run(camera):
    logger.info("Generating app...")
    app = pg.mkQApp("Stroboscopic imaging")

    def intHandler(sig, frame):
        app.quit()

    signal.signal(signal.SIGINT, intHandler)

    processing_thread = ProcessingProcess(DemodRecordingQueue(10, 1e-9, 1e-10))
    image_acquisition_thread = ImageAcquisitionThread(camera, processing_thread)
    win = SMainWindow()

    # init window
    win.show()

    win.setValidators()
    win.setFrequencySelectorLogic()

    def detuning_update():
        try:
            detuning = float(win.ui.detuning.text())
        except ValueError:
            logging.INFO("Didn't set the detuning")
            return
        pulsation = 2 * np.pi * detuning / 1e9  # nano seconds ^ -1
        processing_thread.messages.put(
            {
                "pulsation": pulsation,
                "discrete_bw": pulsation / 10,
            }
        )

    win.ui.detuning_field.editingFinished.connect(detuning_update)

    def update():
        if not image_acquisition_thread.image_queue.empty():
            ts, img = image_acquisition_thread.image_queue.get_nowait()
            win.ui.raw_img.setImage(img, autoLevels=False)
            logger.debug(f"Updated image at timestamp {ts}")
        else:
            logger.debug("Queue empty, not updating")
        processed_or_none = processing_thread.get()
        if processed_or_none is not None:
            ts, img = processed_or_none
            win.ui.processed_img.setImage(img)
            logger.debug(f"Updated image at timestamp {ts}")
        else:
            logger.debug("No processed data, not updating")

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
    image_acquisition_thread.stop()
    image_acquisition_thread.join()
    processing_thread.stop()
    processing_thread.join()

    logger.info("App terminated. Goodbye!")


if __name__ == "__main__":
    logger.info(f"Hello, my pid is {os.getpid()}")
    # with TLCameraSDK() as sdk:
    #    camera_list = sdk.discover_available_cameras()
    #    with sdk.open_camera(camera_list[0]) as camera:
    camera = FakeCam()
    run(camera)
    sys.exit(0)
