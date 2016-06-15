
import sensor
from mySerial import mySerial
import serial

class Dylos(sensor.Sensor):
	requiredData = ["port","sensorName"]
	optionalData = ["bufsize","timeout"]
	def __init__(self,data):
		self.sensorName = data["sensorName"]
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
			self.dev = mySerial(
				port=data["port"],
				baudrate=9600,
				bytesize=serial.EIGHTBITS,
				parity=serial.PARITY_NONE,
				stopbits=serial.STOPBITS_ONE,
				xonxoff=0,
				rtscts=0,
				dsrdtr=0,
				timeout=self.timeout # Seconds
			)
		except serial.serialutil.SerialException:
			sys.stderr.write("error opening %s\n" % sensorName)
			raise SystemExit(1)
		
	def getVal(self):
		data = self.dev.nonblocking_read(self.bufsize)
		