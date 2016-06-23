import os
import output
import pifacereleyplus as reley

class Relay(output.Output):
    requiredData = ["sensorNames","threshold"]
    optionalData = []
    def __init__(self,data):
        self.sensorNames = [s.strip() for s in data['sensorNames'].split(',')]
        self.threshold = int(data['threshold'])
        pfr = relay.PiFaceRelayPlus(relay.RELAY)
        self.lastdata = 0
    def outputData(self,dataPoints):
        """
        The data comes in as a dictionary
        """
        data = dataPoints["value"]
        sensorName = dataPoints["sensorName"]
        if sensorName in self.sensorName:
			if data > self.threshold and laststate == "off":
				pfr.relays[0].toggle()
				self.laststate = "on"
			elif data < self.threshold and laststate == "on":
				pfr.relays[0].toggle()
				self.laststate = "off"