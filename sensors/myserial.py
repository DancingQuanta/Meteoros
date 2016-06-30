
import sensor
import serial

class MySerial(sensor.Sensor):
	requiredData = ["port","baudrate","rtscts",
		"dsrdtr","xonxoff","sensorName"]
	optionalData = ["bufsize","timeout"]
	def __init__(self,data):
		# Default settings
		if "bufsize" in data:
			self.bufsize = data["bufsize"]
		else:
			self.bufsize = 65536
		if "timeout" in data:
			self.timeout = int(data["timeout"])
		else:
			self.timeout = 0.1
		class ConfigError(Exception): pass
		try:
			self.dev = serial.Serial(
				port=data["port"],
				baudrate=int(data["baudrate"]),
				bytesize=serial.EIGHTBITS,
				parity=serial.PARITY_NONE,
				stopbits=serial.STOPBITS_ONE,
				xonxoff=data["xonxoff"],
				rtscts=data["rtscts"],
				dsrdtr=data["dsrdtr"],
				timeout=self.timeout # Seconds
			)
		except sensor.sensorutil.SerialException:
			sys.stderr.write("error opening %s\n" % node)
			raise SystemExit(1)
		
	
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
		
	def getVal(self):
		data = self.nonblocking_read(self.bufsize)
		
