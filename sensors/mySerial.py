
import select
import os
import errno
import serial
from serial import SerialException


class mySerial(serial.Serial):
    def nonblocking_read(self, size=1):
        [r, w, x] = select.select([self.fd], [], [self.fd], self._timeout)
        if r:
            try:
                return os.read(self.fd, size)
            except OSError as e:
                if e.errno == errno.EAGAIN:
                    return None
                    raise
        eli:
            raise SerialException("exception (device disconnected?)")
        else:
            return None  # timeout
