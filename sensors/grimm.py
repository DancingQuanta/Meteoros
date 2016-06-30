import sensor
from mySerial import mySerial
import serial

class Grimm(sensor.Sensor):
  """
  The data outputted by Grimm is complex
  """
  requiredData = ["port","sensorName"]
  optionalData = ["bufsize","timeout"]
  def __init__(self,data):
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
      return self.data
