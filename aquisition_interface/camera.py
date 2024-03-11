"""
"""

import logging
import queue
import threading
import time

import numpy as np

logger = logging.getLogger(__name__)


class ImageAcquisitionThread(threading.Thread):
    def __init__(self, camera, processor, **kwargs):
        super().__init__(**kwargs)
        self.camera = camera
        # Do not want to block for long periods of time
        self.camera.image_poll_timeout_ms = 0
        self.image_queue = queue.Queue(maxsize=2)
        self.processor = processor
        self.stop_event = threading.Event()

    def stop(self):
        self.stop_event.set()

    def run(self):
        while not self.stop_event.is_set():
            try:
                frame = self.camera.get_pending_frame_or_null()
                if frame is not None:
                    image = np.copy(frame.image_buffer)
                    timestamp = frame.time_stamp_relative_ns_or_null
                    try:
                        self.processor.put(timestamp, image)
                    except queue.Full:
                        logger.warning("1 frame droped for the processing")
                    try:
                        self.image_queue.put_nowait((timestamp, np.copy(image)))
                    except queue.Full:
                        logger.warning("1 frame droped for the display")

            except Exception as error:
                logger.error(
                    f"Encountered error: {error}, image acquisition will stop."
                )
                break
            time.sleep(1 / 30)
        logger.info("Image acquisition has stopped")
