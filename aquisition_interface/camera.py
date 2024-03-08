"""
"""

import logging
import queue

import numpy as np
from PyQt5.QtCore import QThread, QTimer, pyqtSignal

logger = logging.getLogger(__name__)


class ImageAcquisitionThread(QThread):
    new_frame = pyqtSignal(int, np.ndarray)

    def __init__(self, camera, **kwargs):
        super().__init__(**kwargs)
        self.camera = camera
        # Do not want to block for long periods of time

    def run(self):
        def getFrameIfAny():
            try:
                frame = self.camera.get_pending_frame_or_null()
                if frame is not None:
                    image = np.copy(frame.image_buffer)
                    timestamp = frame.time_stamp_relative_ns_or_null
                    try:
                        self.new_frame.emit(timestamp, np.copy(image))
                    except queue.Full:
                        logger.warning("1 frame droped")

            except Exception as error:
                logger.error(f"Encountered error: {error}")

        timer = QTimer()
        timer.timeout.connect(getFrameIfAny)

        logger.info("Setting camera parameters...")
        self.camera.image_poll_timeout_ms = 0
        self.camera.frames_per_trigger_zero_for_unlimited = 0
        # This buffer size comes from thorlabs' live camera example. Let's keep it
        self.camera.arm(2)

        # start acquisition
        timer.start(10)

        # launch the camera
        self.camera.issue_software_trigger()

        # Launch event loop
        self.exec()
        logger.info("Image acquisition has stopped")
