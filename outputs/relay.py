import output
import pifacereleyplus as relay


class Relay(output.Output):
    requiredData = ["sensorNames", "threshold"]
    optionalData = []

    def __init__(self, data):
        self.sensorNames = [s.strip() for s in data['sensorNames'].split(',')]
        self.threshold = int(data['threshold'])
        self.pfr = relay.PiFaceRelayPlus(relay.RELAY)
        self.lastdata = 0

    def outputData(self, dataPoints):
        """
        The data comes in as a dictionary
        """
        data = dataPoints["value"]
        sensorName = dataPoints["sensorName"]
        if sensorName in self.sensorName:
            if data > self.threshold and self.laststate == "off":
                self.pfr.relays[0].toggle()
                self.laststate = "on"
            elif data < self.threshold and self.laststate == "on":
                self.pfr.relays[0].toggle()
                self.laststate = "off"
