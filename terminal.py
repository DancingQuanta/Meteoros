#!/usr/bin/python

# Jim Paris <jim@jtan.com>

# Simple terminal program for serial devices.  Supports setting
# baudrates and simple LF->CRLF mapping on input, and basic
# flow control, but nothing fancy.

# ^C quits.  There is no escaping, so you can't currently send this
# character to the remote host.  Piping input or output should work.

# Supports multiple serial devices simultaneously.  When using more
# than one, each device's output is in a different color.  Input
# is directed to the first device, or can be sent to all devices
# with --all.

import sys
import os
import threading
import traceback
import time
import signal
import fcntl
import string
import re
import ConfigParser
import inspect
from sensors import sensor
from outputs import output
import select, errno

class JimtermColor(object):
	def __init__(self):
		self.setup(1)
	def setup(self, total):
		if total > 1:
			self.codes = [
				"\x1b[1;36m", # cyan
				"\x1b[1;33m", # yellow
				"\x1b[1;35m", # magenta
				"\x1b[1;31m", # red
				"\x1b[1;32m", # green
				"\x1b[1;34m", # blue
				"\x1b[1;37m", # white
				]
			self.reset = "\x1b[0m"
		else:
			self.codes = [""]
			self.reset = ""
	def code(self, n):
		return self.codes[n % len(self.codes)]

class Jimterm:
	"""Normal interactive terminal"""

	def __init__(self,
				 sensors,
				 add_cr = False,
				 raw = True,
				 color = True,
				 logfiledir = None,
				 bufsize = 65536):

		self.color = JimtermColor()
		if color:
			self.color.setup(len(sensors))

		self.sensors = sensors
		self.last_color = ""
		# The last index for which we were outputting (kept around to
		# track when we should make a note of it changing, as with
		# self.last_color):
		self.last_index = None
		self.threads = []
		self.add_cr = add_cr
		self.raw = raw
		self.bufsize = bufsize
		# self.logfiledir & self.log are either None and a do-nothing
		# function, or they are the open log file and a function which
		# writes data to the log:
		if logfiledir:
			self.logfiledir = logfiledir
		else:
			self.logfiledir = None
		self.quote_re = None
	
	def print_header(self, nodes, output = sys.stdout):
		for (n, (node,)) in enumerate(zip(nodes)):
			output.write(self.color.code(n)
						 + node + self.color.reset + "\n")
		if sys.stdin.isatty():
			output.write("^C to exit\n")
			output.write("----------\n")
		output.flush()

	def start(self):
		self.alive = True

		# sensor data->console, all devices
		for (n, serial) in enumerate(self.sensors):
			self.threads.append(threading.Thread(
				target = self.reader,
				args = (serial, self.color.code(n), n)
				))

		# start all threads
		for thread in self.threads:
			thread.daemon = True
			thread.start()

	def stop(self):
		self.alive = False

	def join(self):
		for thread in self.threads:
			while thread.isAlive():
				thread.join(0.1)

			self.quote_func = qf
		return self.quote_re.sub(self.quote_func, data)

	# def quote_raw(self, data):
		# if self.quote_re is None:
			# matcher = '[^%s]' % re.escape(string.printable + "\b")
			# if sys.version_info < (3,):
				# self.quote_re = re.compile(matcher)
				# qf = lambda x: ("\\x%02x" % ord(x.group(0)))
			# else:
				# self.quote_re = re.compile(matcher.encode('ascii'))
				# qf = lambda x: ("\\x%02x" % ord(x.group(0))).encode('ascii')
			# self.quote_func = qf
		# return self.quote_re.sub(self.quote_func, data)
	
	def logger(self,dev,data):
		if self.logfiledir:
			today = time.strftime("%Y-%m-%d-%H", time.localtime())
			node = dev.port.replace('/','-')
			logfile = os.path.join(self.logfiledir, today) +"-" + node
			with open(logfile, 'a') as f: # Open log file
					f.write(data)
					f.flush() # Properly write to disk
					
	def reader(self, sensor, color, index):
		"""Loop and copy sensor->console.  'sensor' is the sensor device,
		'color' is the string for the current color, 'index' is the current
		device index corresponding to 'sensor'."""

		# Get details of the sensor and add to dict
		dataDict = {}
		dataDict["unit"] = sensor.valUnit
		dataDict["symbol"] = sensor.valSymbol
		dataDict["name"] = sensor.valName
		dataDict["sensor"] = sensor.sensorName
		try:
			while self.alive:
				if (curTime-lastUpdated)>delayTime:
					lastUpdated = curTime
					data = []
					#Collect the data from a sensor
					val = sensor.getVal()
					if val==None: #this means it has no data to upload.
						continue
					dataDict["value"] = sensor.getVal()
					working = True
					for i in outputPlugins:
						working = working and sensor.outputData(dataDict)
					if working:
						print "Uploaded successfully"
					else:
						print "Failed to upload"

				if color != self.last_color:
					self.last_color = color
					os.write(sys.stdout.fileno(), color.encode("utf-8"))

				if index != self.last_index:
					self.last_index = index

				if self.add_cr:
					if sys.version_info < (3,):
						data = data.replace('\n', '\r\n')
					else:
						data = data.replace(b'\n', b'\r\n')

				# if not self.raw:
					# data = self.quote_raw(data)

				os.write(sys.stdout.fileno(), data)
		except Exception as e:
			sys.stdout.write(color)
			sys.stdout.flush()
			traceback.print_exc()
			sys.stdout.write(self.color.reset)
			sys.stdout.flush()
			os._exit(1)

	def run(self):
		# Set all sensor port timeouts to 0.1 sec
		saved_timeouts = []
		for sensor in self.sensors:
			saved_timeouts.append(sensor.timeout)
			sensor.timeout = 0.1

		# Handle SIGINT gracefully
		signal.signal(signal.SIGINT, lambda *args: self.stop())

		# Go
		self.start()
		self.join()

		# Restore sensor port timeouts
		for (sensor, saved) in zip(self.sensors, saved_timeouts):
			sensor.timeout = saved

		# Cleanup
		sys.stdout.write(self.color.reset + "\n")
		
if __name__ == "__main__":
	import argparse
	import re

	formatter = argparse.ArgumentDefaultsHelpFormatter
	description = ("Based on AirPi and terminal.py the program "
				         "logs data from connected sensors."
				   "The outputs are shown in varying colors.")
	parser = argparse.ArgumentParser(description = description,
									 formatter_class = formatter)

	parser.add_argument("--quiet", "-q", action="store_true",
						help="Don't print header")

	parser.add_argument("--crlf", "-c", action="store_true",
						help="Add CR before incoming LF")
	parser.add_argument("--mono", "-m", action="store_true",
						help="Don't use colors in output")
	parser.add_argument("--bufsize", "-z", metavar="SIZE", type=int,
						help="Buffer size for reads and writes", default=65536)

	group = parser.add_mutually_exclusive_group(required = False)
	group.add_argument("--raw", "-r", action="store_true",
					   default=argparse.SUPPRESS,
					   help="Output characters directly "
					   "(default, if stdout is not a tty)")
	group.add_argument("--no-raw", "-R", action="store_true",
					   default=argparse.SUPPRESS,
					   help="Quote unprintable characters "
					   "(default, if stdout is a tty)")

	args = parser.parse_args()
	
	piped = not sys.stdout.isatty()
	raw = "raw" in args or (piped and "no_raw" not in args)
	
	# Load settings.cfg
	if os.path.isfile("settings.cfg"):
		mainConfig = ConfigParser.SafeConfigParser()
		mainConfig.read("settings.cfg")
		try:
			logfiledir = mainConfig.get("Main","logfiledir")
			# Check if local logging directory exists
			if not os.path.exists(logfiledir):
				os.makedirs(logfiledir)
		except:
			print("Not logging to file!")
			logfiledir = None
	else:
		print "Unable to access config file: settings.cfg"
	
	# Load configuration from various sensors
	if not os.path.isfile('sensors.cfg'):
		print "Unable to access config file: sensors.cfg"
		exit(1)
		
	# Load sensor configuration
	def get_subclasses(mod,cls):
		for name, obj in inspect.getmembers(mod):
			if hasattr(obj, "__bases__") and cls in obj.__bases__:
				return obj
		
	sensorConfig = ConfigParser.SafeConfigParser()
	sensorConfig.read('sensors.cfg')
	sensorNames = sensorConfig.sections()

	sensorPlugins = []
	for i in sensorNames:
		try:	
			try:
				filename = sensorConfig.get(i,"filename")
			except Exception:
				print("Error: no filename config option found for sensor plugin " + i)
				raise
			try:
				enabled = sensorConfig.getboolean(i,"enabled")
			except Exception:
				enabled = True

			#if enabled, load the plugin
			if enabled:
				try:
					mod = __import__('sensors.'+filename,fromlist=['a']) #Why does this work?
				except Exception:
					print("Error: could not import sensor module " + filename)
					raise

				try:	
					sensorClass = get_subclasses(mod,sensor.Sensor)
					if sensorClass == None:
						raise AttributeError
				except Exception:
					print("Error: could not find a subclass of sensor.Sensor in module " + filename)
					raise

				try:	
					reqd = sensorClass.requiredData
				except Exception:
					reqd =  []
				try:
					opt = sensorClass.optionalData
				except Exception:
					opt = []

				pluginData = {}

				class MissingField(Exception): pass
							
				for requiredField in reqd:
					if sensorConfig.has_option(i,requiredField):
						pluginData[requiredField]=sensorConfig.get(i,requiredField)
					else:
						print "Error: Missing required field '" + requiredField + "' for sensor plugin " + i
						raise MissingField
				for optionalField in opt:
					if sensorConfig.has_option(i,optionalField):
						pluginData[optionalField]=sensorConfig.get(i,optionalField)
				instClass = sensorClass(pluginData)
				sensorPlugins.append(instClass)
				print ("Success: Loaded sensor plugin " + i)
		except Exception as e: #add specific exception for missing module
			print("Error: Did not import sensor plugin " + i )
			raise e

	term = Jimterm(sensorPlugins,
				   add_cr = args.crlf,
				   raw = raw,
				   color = (os.name == "posix" and not args.mono),
				   logfiledir = logfiledir,
				   bufsize = args.bufsize)
	if not args.quiet:
		term.print_header(sensorNames, sys.stderr)

	term.run()
