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
import serial
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

class MySerial(serial.Serial):
	def nonblocking_read(self, size=1):
		[r, w, x] = select.select([self.fd], [], [self.fd], self._timeout)
		if r:
			try:
				return os.read(self.fd, size)
			except OSError as e:
				if e.errno == errno.EAGAIN:
					return None
				raise
		elif x:
			raise SerialException("exception (device disconnected?)")
		else:
			return None # timeout

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
				 serials,
				 suppress_write_bytes = None,
				 suppress_read_firstnull = True,
				 transmit_all = False,
				 add_cr = False,
				 raw = True,
				 color = True,
				 logfiledir = None,
				 bufsize = 65536):

		self.color = JimtermColor()
		if color:
			self.color.setup(len(serials))

		self.serials = serials
		self.suppress_write_bytes = suppress_write_bytes
		self.suppress_read_firstnull = suppress_read_firstnull
		self.last_color = ""
		# The last index for which we were outputting (kept around to
		# track when we should make a note of it changing, as with
		# self.last_color):
		self.last_index = None
		self.threads = []
		self.transmit_all = transmit_all
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
	
	def logger(self,dev,data):
		if self.logfiledir:
			today = time.strftime("%Y-%m-%d-%H", time.localtime())
			node = dev.port.replace('/','-')
			logfile = os.path.join(self.logfiledir, today) +"-" + node
			with open(logfile, 'a') as f: # Open log file
					f.write(data)
					f.flush() # Properly write to disk
	
	def print_header(self, nodes, bauds, output = sys.stdout):
		for (n, (node, baud)) in enumerate(zip(nodes, bauds)):
			output.write(self.color.code(n)
						 + node + ", " + str(baud) + " baud"
						 + self.color.reset + "\n")
		if sys.stdin.isatty():
			output.write("^C to exit\n")
			output.write("----------\n")
		output.flush()

	def start(self):
		self.alive = True

<<<<<<< HEAD
		# Set up console
		self.console = Console(self.bufsize)

		# serial->console, all devices
		for (n, serial) in enumerate(self.serials):
=======
		# sensor data->console, all devices
		for (n, serial) in enumerate(self.sensors):
>>>>>>> 8e51ce3... Removed Console class and its instances because the class is not needed and is blocking the keyboard from interrupting the script.
			self.threads.append(threading.Thread(
				target = self.reader,
				args = (serial, self.color.code(n), n)
				))

		# console->serial
		self.threads.append(threading.Thread(target = self.writer))

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
					
	def reader(self, serial, color, index):
		"""Loop and copy serial->console.  'serial' is the serial device,
		'color' is the string for the current color, 'index' is the current
		device index corresponding to 'serial'."""
		first = True
		try:
			if (sys.version_info < (3,)):
				null = '\x00'
			else:
				null = b'\x00'
			while self.alive:
				data = serial.nonblocking_read(self.bufsize)
				if data is None:
					continue
				if not len(data):
					raise Exception("read returned EOF")

				# don't print a NULL if it's the first character we
				# read.  This hides startup/port-opening glitches with
				# some serial devices.
				if self.suppress_read_firstnull and first and data[0] == null:
					first = False
					data = data[1:]
				first = False

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
				self.logger(serial,data.decode("utf-8"))
		except Exception as e:
			sys.stdout.write(color)
			sys.stdout.flush()
			traceback.print_exc()
			sys.stdout.write(self.color.reset)
			sys.stdout.flush()
			self.logger(serial,"\nKilled with exception: %s" % (e,))
			os._exit(1)
	
	def writer(self):
		"""loop and copy console->serial until ^C"""
		try:
			if (sys.version_info < (3,)):
				ctrlc = '\x03'
			else:
				ctrlc = b'\x03'
			while self.alive:
				try:
					c = self.console.getkey()
				except KeyboardInterrupt:
					self.stop()
					return
				if c is None:
					# No input, try again.
					continue
				elif self.console.tty and ctrlc in c:
					# Try to catch ^C that didn't trigger KeyboardInterrupt
					self.stop()
					return
				elif c == '':
					# Probably EOF on input.  Wait a tiny bit so we can
					# flush the remaining input, then stop.
					time.sleep(0.25)
					self.stop()
					return
				else:
					# Remove bytes we don't want to send
					if self.suppress_write_bytes is not None:
						c = c.translate(None, self.suppress_write_bytes)

					# Send character
					if self.transmit_all:
						for serial in self.serials:
							serial.write(c)
					else:
						self.serials[0].write(c)
		except Exception as e:
			self.console.cleanup()
			sys.stdout.write(self.color.reset)
			sys.stdout.flush()
			traceback.print_exc()
			os._exit(1)

	def run(self):
		# Set all serial port timeouts to 0.1 sec
		saved_timeouts = []
		for serial in self.serials:
			saved_timeouts.append(serial.timeout)
			serial.timeout = 0.1

		# Work around https://sourceforge.net/p/pyserial/bugs/151/
		saved_writeTimeouts = []
		for serial in self.serials:
			saved_writeTimeouts.append(serial.writeTimeout)
			serial.writeTimeout = 1000000

		# Handle SIGINT gracefully
		signal.signal(signal.SIGINT, lambda *args: self.stop())

		# Go
		self.start()
		self.join()

		# Restore serial port timeouts
		for (serial, saved) in zip(self.serials, saved_timeouts):
			serial.timeout = saved
		for (serial, saved) in zip(self.serials, saved_writeTimeouts):
			serial.writeTimeout = saved

		# Cleanup
		sys.stdout.write(self.color.reset + "\n")
		
if __name__ == "__main__":
	import argparse
	import re

	formatter = argparse.ArgumentDefaultsHelpFormatter
	description = ("Simple serial terminal that supports multiple devices.  "
				   "If more than one device is specified, device output is "
				   "shown in varying colors.  All input goes to the "
				   "first device.")
	parser = argparse.ArgumentParser(description = description,
									 formatter_class = formatter)

	parser.add_argument("--quiet", "-q", action="store_true",
						help="Don't print header")

	parser.add_argument("--crlf", "-c", action="store_true",
						help="Add CR before incoming LF")
	parser.add_argument("--all", "-a", action="store_true",
						help="Send keystrokes to all devices, not just "
						"the first one")
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
		
	sensorConfig = ConfigParser.SafeConfigParser()
	sensorConfig.read('sensors.cfg')
	sensorNames = sensorConfig.sections()

	devs = []
	nodes = []
	bauds = []
	for i in sensorNames:
		try:	
			try:
				filename = sensorConfig.get(i,"filename")
			except Exception:
				print("Error: no filename config option found for sensor plugin " + i)
				raise
			try:
				node = sensorConfig.get(i,"node")
			except Exception:
				print("Error: no port config option found for sensor plugin " + i)
				raise
			try:
				baud = sensorConfig.get(i,"baud")
			except Exception:
				print("Error: no baudrate config option found for sensor plugin " + i)
				raise
			try:
				rtscts = sensorConfig.get(i,"rtscts")
			except Exception:
				print("Error: no rtscts config option found for sensor plugin " + i)
				raise
			try:
				xonxoff = sensorConfig.get(i,"xonxoff")
			except Exception:
				print("Error: no xonxoff config option found for sensor plugin " + i)
				raise
			try:
				dsrdtr = sensorConfig.get(i,"dsrdtr")
			except Exception:
				print("Error: no dsrdtr config option found for sensor plugin " + i)
				raise
			try:
				enabled = sensorConfig.getboolean(i,"enabled")
			except Exception:
				enabled = True
			if node in nodes:
				sys.stderr.write("error: %s specified more than once\n" % node)
				raise SystemExit(1)
			try:
				dev = MySerial(
					node,
					baud,
					xonxoff = xonxoff,
					rtscts = rtscts,
					dsrdtr = dsrdtr
				)
			except serial.serialutil.SerialException:
				sys.stderr.write("error opening %s\n" % node)
				raise SystemExit(1)
			nodes.append(node)
			bauds.append(baud)
			devs.append(dev)
		except Exception as e: #add specific exception for missing module
			print("Error: Did not import sensor plugin " + i )
			raise e

	term = Jimterm(devs,
				   transmit_all = args.all,
				   add_cr = args.crlf,
				   raw = raw,
				   color = (os.name == "posix" and not args.mono),
				   logfiledir = logfiledir,
				   bufsize = args.bufsize)
	if not args.quiet:
		term.print_header(nodes, bauds, sys.stderr)

	term.run()
