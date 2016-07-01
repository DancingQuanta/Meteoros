
import sensor
from mySerial import mySerial
import serial
import datetime as dt
import sys

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
		self.data = ""
		self.data = self.dev.nonblocking_read(self.bufsize)
		if self.data==None:
			return self.data
		else:
			while "\n" not in self.data:
				self.data = self.data + self.dev.nonblocking_read(self.bufsize)
			now = dt.datetime.now()
			data = self.data
			try:
				bin_data = [int(x.strip()) for x in data.split(',')]
			except:
				#Dylos Error
				print("Dylos Data: Error - Dylos Bin data")
				return None
			if len(bin_data) >= 2:
				bin_1=bin_data[0]
				bin_2=bin_data[1]
			else:
				bin_1=-9999
				bin_2=-9999
			data =  "%s,%s,%s\n" % (now,bin_1,bin_2)
			return data
