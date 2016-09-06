from . import Sensor
import time


class Dummy(Sensor):
    """Timer sensor class for testing the program
    """
    requiredData = ["sensorName", "delay"]
    optionalData = []

    def __init__(self, data):
        self.sensorName = data["sensorName"]
        self.delay = int(data["delay"])
        self.curTime = 0
        self.lastUpdated = 0

    def getVal(self):
        self.curTime = time.time()
        if (self.curTime-self.lastUpdated) > self.delay:
            self.lastUpdated = self.curTime
            return str(self.curTime) + "\n"
