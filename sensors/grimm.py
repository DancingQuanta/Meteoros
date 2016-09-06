from . import Sensor
from mySerial import mySerial
import serial
import sys


class Grimm(Sensor):
    """
    The data outputted by Grimm is complex
    """
    requiredData = ["port", "sensorName"]
    optionalData = ["bufsize", "timeout"]

    def __init__(self, data):
        self.datetime = None
        self.data = None
        self.sensorName = data["sensorName"]
        # Default settings
        if "bufsize" in data:
            self.bufsize = int(data["bufsize"])
        else:
            self.bufsize = 250
        if "timeout" in data:
            self.timeout = float(data["timeout"])
        else:
            self.timeout = 0.1

        class ConfigError(Exception): pass

        serial_opts = {"port": data["port"],
                       "baudrate": 9600,
                       "bytesize": serial.EIGHTBITS,
                       "parity": serial.PARITY_NONE,
                       "stopbits": serial.STOPBITS_ONE,
                       "xonxoff": False,
                       "rtscts": False,
                       "dsrdtr": False,
                       "timeout": self.timeout}  # Seconds

        try:
            self.dev = mySerial(**serial_opts)
        except serial.serialutil.SerialException:
            sys.stderr.write("error opening %s\n" % self.sensorName)
            raise SystemExit(1)

    def getVal(self):
        self.data = ""
        self.data = self.dev.nonblocking_read(self.bufsize)
        if self.data is None:
            return self.data
        else:
            while "\n" not in self.data:
                self.data = self.data + self.dev.nonblocking_read(self.bufsize)
            return self.data
