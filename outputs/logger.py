import time
import os
import subprocess
import output

class Logger(output.Output):
	requiredData = ["localdir"]
	optionalData = ["remotedir","remoteuser","remotehostname"]
	def __init__(self,data):

		self.ld = data["localdir"]
		# Check if local logging directory exists
		if not os.path.exists(self.ld):
			os.makedirs(self.ld)
		
		if "remotedir" in data:
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

	def write(self,sensorName,data):
		today = time.strftime("%Y-%m-%d-%H", time.localtime())
		logfile = os.path.join(self.ld, today) +"-" + sensorName
		with open(logfile, 'a') as f: # Open log file
				f.write(data)
				f.flush() # Properly write to disk
	
	def backup(self,ld,rd,raddr):
		# local dir, remote dir and remote address
		# Backup data to server
		
		# Here we format the remote location as 'username@hostname:'location'
		remote = "%s:'%s'" % (raddr, rd)	
		
		# rsync
		rsync_cmd = 'rsync -arz %s/ %s/' % (ld, remote)
		p = subprocess.Popen(rsync_cmd, shell=True).wait()	
		
	def outputData(self,dataPoints):
		"""
		The data comes in as a dictionary
		"""
		data = dataPoints["value"]
		sensorName = dataPoints["sensorName"]
		self.write(sensorName,data)
		if self.rd != None and self.raddr != None:
		        self.backup(self.ld,self.rd,self.raddr)
