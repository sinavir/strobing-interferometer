"""
"""

import logging
import multiprocessing
import signal
import time
from queue import Full

import numpy as np

logger = logging.getLogger(__name__)


class ProcessingProcess(multiprocessing.Process):
    def __init__(self, processor, **kwargs):
        super().__init__(**kwargs)
        self.in_queue = multiprocessing.Queue(maxsize=2)
        self.out_queue = multiprocessing.Queue(maxsize=2)
        self.messages = multiprocessing.Queue()
        self.stop_event = multiprocessing.Event()
        self.records = processor

    def stop(self):
        self.stop_event.set()
        while not self.out_queue.empty():
            self.out_queue.get()
        while not self.in_queue.empty():
            self.in_queue.get()
        while not self.messages.empty():
            self.messages.get()

    def put(self, ts, img):
        logger.debug("Queuing for processing")
        self.in_queue.put_nowait((ts, img))

    def get(self):
        if self.out_queue.empty():
            return None
        logger.debug("Got a processed image")
        return self.out_queue.get_nowait()

    def run(self):
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        while not self.stop_event.is_set():
            if not self.messages.empty():
                attrs = self.messages.get_nowait()
                for k in attrs:
                    setattr(self.records, k, attrs[k])
            if not self.in_queue.empty():
                ts, frame = self.in_queue.get_nowait()
                rslt = self.records.enqueue(ts, frame)
                if rslt is None:
                    continue
                try:
                    self.out_queue.put_nowait(rslt)
                    print("put processed frame")
                except Full:
                    pass


class RecordingQueue:
    def __init__(self, length, compute_period=5):
        super().__init__()
        # allocate the memory we need ahead of time
        self.max_length = length
        self.queue_tail = length - 1
        self.rec_queue = None
        self.timestamps = None
        self._temp_rec_queue = []
        self._temp_timestamps = []
        self.compute_period = compute_period
        self.counter = 0

    def enqueue(self, ts, new_data):
        if self.rec_queue is None:
            self._temp_rec_queue.append(new_data)
            self._temp_timestamps.append(ts)
            if len(self._temp_rec_queue) >= self.max_length:
                self.beginProcessing()
            return None
        # move tail pointer forward then insert at the tail of the queue
        # to enforce max length of recording
        self.queue_tail = (self.queue_tail + 1) % self.max_length
        self.rec_queue[self.queue_tail] = new_data
        self.timestamps[self.queue_tail] = ts
        self.compute_fast()
        self.counter += 1
        if self.counter == self.compute_period:
            self.counter = 0
            return self.compute_slow()
        return None

    def compute_fast(self):
        pass

    def compute_slow(self):
        raise NotImplementedError

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

    def compute_slow(self):
        return (self.timestamps[self.queue_tail], self.std())

    def std(self):
        return np.std(self.rec_queue, axis=0)

    def mean(self):
        return np.mean(self.rec_queue, axis=0)


class DemodRecordingQueue(RecordingQueue):
    def __init__(self, length, pulsation, discrete_bw, compute_period=1):
        super().__init__(length, compute_period)
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
        for i in range(1, self.max_length):
            self.computeOutput(at=i)

    def computeOutput(self, at=None):
        if at is None:
            at = self.queue_tail
        prev = (at - 1) % self.max_length
        # Add a correction to the bandwisth since the images are not perfectly spaced a priori
        w = self.discrete_bw * (self.timestamps[at] - self.timestamps[prev])
        self.output = (1 - w) * self.output + w * self.demodulated[at]

    def compute_fast(self):
        ts = self.timestamps[self.queue_tail]
        self.demodulated[self.queue_tail] = self.rec_queue[self.queue_tail] * np.exp(
            1.0j * self.pulsation * ts
        )
        self.computeOutput()

    def compute_slow(self):
        ts = self.timestamps[self.queue_tail]
        return (ts, np.absolute(self.output))
