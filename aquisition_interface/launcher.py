import logging
import os
import signal

import pyqtgraph as pg
from PyQt5 import QtCore

from .camera import ImageAcquisitionThread
from .fake_cam import FakeCam
from .processing import ProcessingProcess
from .window import SMainWindow

# from thorlabs_tsi_sdk.tl_camera import TLCameraSDK

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

""" Main
"""

def run(camera):
    logger.info("Generating app...")
    app = pg.mkQApp("Stroboscopic imaging")

    processing_thread = ProcessingProcess()
    image_acquisition_thread = ImageAcquisitionThread(camera, processing_thread)
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

    logger.debug("Setting up signals")

    def intHandler(sig, frame):
        app.quit()

    signal.signal(signal.SIGINT, intHandler)
    app.exec()

    logger.info("Waiting for image acquisition thread to finish...")
    processing_thread.stop()
    processing_thread.join()
    image_acquisition_thread.stop()
    image_acquisition_thread.join()

    logger.info("App terminated. Goodbye!")

if __name__ == "__main__":
    logger.info(f"Hello, my pid is {os.getpid()}")
    # with TLCameraSDK() as sdk:
    #    camera_list = sdk.discover_available_cameras()
    #    with sdk.open_camera(camera_list[0]) as camera:
    camera = FakeCam()
    run(camera)
