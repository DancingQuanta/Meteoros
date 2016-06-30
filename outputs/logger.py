import sys
import time
import os
import subprocess
import output
import usbbackup

class Logger(output.Output):
    usbData = ["usb"]
    remoteData = ["remotedir","remoteuser","remotehostname"]
    requiredData = ["localdir"]
    optionalData = remoteData + usbData
    def __init__(self,data):

        self.ld = data["localdir"]
        # Check if local logging directory exists
        if not os.path.exists(self.ld):
            os.makedirs(self.ld)
        # Check if remoteBackup needs to be enabled
        if set(self.remoteData) <= set(data):
            # Check if remoteData is subset of list of keys of data to ensure all remote settings are available
            rd = data["remotedir"]
            ru = data["remoteuser"]
            rh = data["remotehostname"]
            #Remote address
            raddr = "%s@%s" % (ru, rh)
            # Ensure that remote address exists
            # Create remote directory if does not exist
            mkdir_cmd = 'ssh %s "mkdir -p %s"' % (raddr,rd)
            p = subprocess.Popen(mkdir_cmd, shell=True).wait()
            self.rd = rd
            self.raddr = raddr
        else:
            print("Warning!: The given remote settings are incomplete so no remote backup!")
            self.rd = None
            self.raddr = None
        # Check if usb backup needs to be enabled
        if set(self.usbData) <= set(data):
            usbStatus = data["usb"]
            if usbStatus == "on":
                self.usbStatus = True
            else:
                print("Warning!: The USB backup is disabled!")
                self.usbStatus = False
        else:
            print("Warning!: The USB backup is disabled!")
            self.usbStatus = False
        # Get datetime to init the variable
        self.lastdatetime = time.strftime("%Y-%m-%d-%H", time.localtime())

    def remoteBackup(self,ld,rd,raddr):
        # local dir, remote dir and remote address
        # Backup data to server

        # Here we format the remote location as 'username@hostname:'location'
        remote = "%s:'%s'" % (raddr, rd)

        # rsync
        rsync_cmd = 'rsync -arz %s/ %s/' % (ld, remote)
        p = subprocess.Popen(rsync_cmd, shell=True).wait()
        # If this successful?
        if p == 0:
          return True
        else:
          return False

    def usbBackup(self,ld):
        # Back up to USB
        media = "/media"
        status = usbbackup.main(ld,media)

    def outputData(self,dataPoints):
        """
        The data comes in as a dictionary
        """
        # Write to disk
        data = dataPoints["value"]
        sensorName = dataPoints["sensorName"]
        datetime = time.strftime("%Y-%m-%d-%H", time.localtime())
        logfile = os.path.join(self.ld, datetime) + "-" + sensorName
        with open(logfile, 'a') as f: # Open log file
            f.write(data)
            f.flush() # Properly write to disk

        # Backup
        usbStatus = False
        if self.rd != None and self.raddr != None:
            remoteStatus = self.remoteBackup(self.ld,self.rd,self.raddr)
        if self.usbStatus:
            usbStatus = self.usbBackup(self.ld)
        if usbStatus or remoteStatus:
            if self.lastdatetime != datetime:
                cmd = "find %s ! -name '%s' -type f -exec rm -f {} +" % (self.ld,logfile)
                p = subprocess.Popen(cmd, shell=True).wait()
                self.lastdatetime = datetime
