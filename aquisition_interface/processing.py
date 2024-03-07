"""
"""

import logging
import queue
import threading

import numpy as np

logger = logging.getLogger(__name__)


class StdProcessing(threading.Thread):
    def __init__(self, in_queue, shape, **kwargs):
        super().__init__(**kwargs)
        self.in_queue = in_queue
        self.out_queue = queue.Queue(maxsize=2)
        self.stop_event = threading.Event()
        self.records = RecordingQueue(np.zeros(shape, dtype=float))

    def stop(self):
        self.stop_event.set()

    def run(self):
        while not self.stop_event.is_set():
            if not self.in_queue.empty():
                ts, frame = self.in_queue.get_nowait()
                self.records.enqueue(frame)
                try:
                    self.out_queue.put_nowait((ts, self.records.std()))
                except queue.Full:
                    logger.warning("1 processed frame droped")
        logger.info("Image processing has stopped")


# https://stackoverflow.com/questions/42771110/fastest-way-to-left-cycle-a-numpy-array-like-pop-push-for-a-queue
class RecordingQueue:
    def __init__(self, object: object):
        # allocate the memory we need ahead of time
        self.max_length: int = len(object)
        self.queue_tail: int = self.max_length - 1
        self.rec_queue = np.array(object)

    def to_array(self) -> np.array:
        head = (self.queue_tail + 1) % self.max_length
        return np.roll(self.rec_queue, -head)  # this will force a copy

    def enqueue(self, new_data: np.array) -> None:
        # move tail pointer forward then insert at the tail of the queue
        # to enforce max length of recording
        self.queue_tail = (self.queue_tail + 1) % self.max_length
        self.rec_queue[self.queue_tail] = new_data

    def peek(self) -> int:
        queue_head = (self.queue_tail + 1) % self.max_length
        return self.rec_queue[queue_head]

    def replace_item_at(self, index: int, new_value: int):
        loc = (self.queue_tail + 1 + index) % self.max_length
        self.rec_queue[loc] = new_value

    def item_at(self, index: int) -> int:
        # the item we want will be at head + index
        loc = (self.queue_tail + 1 + index) % self.max_length
        return self.rec_queue[loc]

    def std(self):
        return np.std(self.rec_queue, axis=0)

    def mean(self):
        return np.mean(self.rec_queue, axis=0)

    def __repr__(self):
        return "tail: " + str(self.queue_tail) + "\narray: " + str(self.rec_queue)

    def __str__(self):
        return "tail: " + str(self.queue_tail) + "\narray: " + str(self.rec_queue)
        # return str(self.to_array())
