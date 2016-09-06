import sensor
import time
from datetime import datetime
import usbiss
import opc


class AlphasenseOPC(sensor.Sensor):
    """Alphasense Optical Particle Counter
    """
    requiredData = ["port", "sensorName", "delay"]

    def __init__(self, data):
        """
        Initialize OPC object, open connection to OPC and turn it on and make
        it ready for measurement.
        """
        self.curTime = 0
        self.lastUpdated = 0
        self.sensorName = data["sensorName"]
        self.delay = int(data["delay"])

        # Connection to OPC
        usb = usbiss.USBISS(data['port'],
                            'spi',
                            spi_mode=2,
                            freq=500000)
        usb.get_iss_info()

        self.alpha = opc.OPCN2(usb)

        self.alpha.off()
        time.sleep(1)
        self.alpha.on()
        time.sleep(1)

        self.alpha.off()
        time.sleep(1)
        self.alpha.on()
        time.sleep(1)

        print(self.alpha.config())
        print(self.alpha.config2())

    def getVal(self):
        curTime = time.time()
        if (curTime-self.lastUpdated) > self.delay:
            self.lastUpdated = curTime

            data = self.alpha.histogram()

            tnow = datetime.fromtimestamp(curTime)

            line = [tnow,
                    data['Bin 0'], data['Bin 1'], data['Bin 2'],
                    data['Bin 3'], data['Bin 4'], data['Bin 5'],
                    data['Bin 6'], data['Bin 7'], data['Bin 8'],
                    data['Bin 9'], data['Bin 10'], data['Bin 11'],
                    data['Bin 12'], data['Bin 13'], data['Bin 14'],
                    data['Bin 15'], data['Bin1 MToF'], data['Bin3 MToF'],
                    data['Bin5 MToF'], data['Bin7 MToF'],
                    data['Sampling Period'], data['Temperature'],
                    data['Pressure'], data['PM1'], data['PM2.5'],
                    data['PM10']]

            data = ','.join(str(e) for e in line) + '\n'
            return data
