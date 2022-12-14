
import serial
import select
import os
import errno

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
		elif x:
			raise SerialException("exception (device disconnected?)")
		else:
			return None # timeout
		