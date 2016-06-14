
import sensor
import serial

class MySerial(sensor.Sensor):
	requiredData = ["port","baudrate","rtscts",
		"dsrdtr","xonxoff","timeout","sensorName"]
	optionalData = ["bufsize"]
	def __init__(self,data):
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
				timeout=int(data["timeout"]) # Seconds
			)
		except sensor.sensorutil.SerialException:
			sys.stderr.write("error opening %s\n" % node)
			raise SystemExit(1)
		if "bufsize" in data:
			self.bufsize = data["bufsize"]
		else:
			self.bufsize = 65536 # Default
		class ConfigError(Exception): pass
	
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
		
