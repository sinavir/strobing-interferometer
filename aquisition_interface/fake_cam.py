import time

import numpy as np


class FakeCam:
    def __init__(self):
        self.frames_per_trigger_zero_for_unlimited = 0
        self.image_poll_timeout_ms = 0
        self.x, self.y = np.meshgrid(np.linspace(0, 10, 1024), np.linspace(0, 10, 1024))
        self.kx = 1.0
        self.ky = 0.5
        self.period = 0.04
        self.omega = 2 * np.pi
        self.last_ts = time.time()

    def issue_software_trigger(self):
        pass

    def arm(self, _buffer):
        pass

    def get_pending_frame_or_null(self):
        if self.last_ts > time.time() - self.period:
            return None
        timestamp = time.time()
        self.last_ts = timestamp
        return FakeFrame(
            timestamp,
            512 * np.sin(self.kx * self.x + self.ky * self.y + timestamp * 2 * np.pi)
            + 521,
        )


class FakeFrame:
    def __init__(self, ts, image):
        self.image_buffer = image
        self.time_stamp_relative_ns_or_null = ts
