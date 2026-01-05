from collections import deque
from threading import Lock
import time  


class ErrorCodes: 
    SHDLC_ERROR_STATE = None 
    QUEUE_FULL = 1
    LOGGER_FAILURE = 2

class MeasurementRingBuffer:
    """
    A thread-safe ring buffer to store measurements.
    """
    def __init__(self, max_size=50):
        self._buffer = deque(maxlen=max_size)
        self._lock = Lock()

    def append(self, measurement):
        with self._lock:
            self._buffer.append(measurement)
            
    def snapshot(self):
        with self._lock:
            return list(self._buffer)
        

class ErrorLogger:
    def __init__(self, path):
        self.path = path
        self._lock = Lock()

    def log(self, code, message, context=None):
        ts = time.time()
        with self._lock, open(self.path, "a") as f:
            f.write(f"[{ts:.6f}] ERROR {code}: {message}\n")
            if context is not None:
                f.write(f"    CONTEXT: {context}\n")
