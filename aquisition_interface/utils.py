import logging
import queue

import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

logger = logging.getLogger(__name__)


class FrameBuffer(QObject):
    new_frame = pyqtSignal(int, np.ndarray)

    def __init__(self, length):
        super().__init__()
        self.length = length
        self.queue = queue.Queue(length)
        self.waiting = False

    @pyqtSlot(int, np.ndarray)
    def enqueue(self, ts, frame):
        try:
            self.queue.put_nowait((ts, frame))
            if self.waiting:
                self.nextIsReady()
        except queue.Full:
            logger.warning("1 frame dropped")

    @pyqtSlot()
    def nextIsReady(self):
        try:
            ts, frame = self.queue.get_nowait()
            self.new_frame.emit(ts, frame)
            self.waiting = False
        except queue.Empty:
            self.waiting = True
