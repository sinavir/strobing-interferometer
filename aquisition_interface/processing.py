"""
"""

import logging

import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

logger = logging.getLogger(__name__)


class RecordingQueue(QObject):
    new_frame = pyqtSignal(int, np.ndarray)
    ready = pyqtSignal()

    def __init__(self, length):
        super().__init__()
        # allocate the memory we need ahead of time
        self.max_length = length
        self.queue_tail = length - 1
        self.rec_queue = None
        self.timestamps = None
        self._temp_rec_queue = []
        self._temp_timestamps = []

    @pyqtSlot(int, np.ndarray)
    def enqueue(self, ts, new_data):
        if self.rec_queue is None:
            self._temp_rec_queue.append(new_data)
            self._temp_timestamps.append(ts)
            if len(self._temp_rec_queue) >= self.max_length:
                self.beginProcessing()
            self.ready.emit()
            return
        # move tail pointer forward then insert at the tail of the queue
        # to enforce max length of recording
        self.queue_tail = (self.queue_tail + 1) % self.max_length
        self.rec_queue[self.queue_tail] = new_data
        self.timestamps[self.queue_tail] = ts
        self.compute()

    def start(self):
        self.ready.emit()

    def compute(self):
        raise NotImplementedError

    def emit(self, ts, frame):
        self.new_frame.emit(ts, frame)
        self.ready.emit()

    def beginProcessing(self):
        """
        Begin the rotating queue process
        """
        self.rec_queue = np.array(self._temp_rec_queue)
        self.timestamps = np.array(self._temp_timestamps)
        del self._temp_rec_queue
        del self._temp_timestamps

    def peek(self):
        queue_head = (self.queue_tail + 1) % self.max_length
        return self.timestamps[queue_head], self.rec_queue[queue_head]

    def __repr__(self):
        return "tail: " + str(self.queue_tail) + "\narray: " + str(self.rec_queue)

    def __str__(self):
        return "tail: " + str(self.queue_tail) + "\narray: " + str(self.rec_queue)


class StatRecordingQueue(RecordingQueue):
    def __init__(self, length):
        super().__init__(length)

    def compute(self):
        self.emit(self.timestamps[self.queue_tail], self.std())

    def std(self):
        return np.std(self.rec_queue, axis=0)

    def mean(self):
        return np.mean(self.rec_queue, axis=0)


class DemodRecordingQueue(RecordingQueue):
    def __init__(self, length, pulsation, discrete_bw):
        super().__init__(length)
        self.pulsation = pulsation
        self.discrete_bw = discrete_bw
        self.demodulated = None
        self.output = None

    def beginProcessing(self):
        super().beginProcessing()
        self.demodulated = (
            self.rec_queue
            * np.exp(1.0j * self.pulsation * self.timestamps)[:, None, None]
        )
        # may be there is an adhoc function for this in numpy
        self.output = self.demodulated[0]
        for i in range(1, self.maxsize):
            self.computeOutput(at=i)

    def computeOutput(self, at=None):
        if at is not None:
            at = self.queue_tail
        prev = (at - 1) % self.max_length
        # Add a correction to the bandwisth since the images are not perfectly spaced a priori
        w = self.discrete_bw * (self.timestamps[at] - self.timestamps[prev])
        self.output = (1 - w) * self.output + w * self.demodulated[at]

    def compute(self):
        ts = self.timestamps[self.queue_tail]
        self.demodulated[self.queue_tail] = self.rec_queue[self.queue_tail] * np.exp(
            1.0j * self.pulsation * ts
        )
        self.computeOutput()
        self.emit(ts, self.output)
