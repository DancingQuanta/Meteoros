#!/usr/bin/python

# Andrew Tolmie <earat@leeds.ac.uk>

# A program that logs data from sensors and pass them to output plugins.
# Each sensor is a defined in a plugin each and is selected in sensors.cfg
# A output plugin works on each sensor's data.

import sys
import os
import threading
import traceback
import time
import signal
# import fcntl
import string
import re
import configparser
import inspect
from sensors import sensor
from outputs import output
import select, errno


class termColor(object):
    def __init__(self):
        self.setup(1)

    def setup(self, total):
        if total > 1:
            self.codes = [
                "\x1b[1;36m",  # cyan
                "\x1b[1;33m",  # yellow
                "\x1b[1;35m",  # magenta
                "\x1b[1;31m",  # red
                "\x1b[1;32m",  # green
                "\x1b[1;34m",  # blue
                "\x1b[1;37m",  # white
                ]
            self.reset = "\x1b[0m"
        else:
            self.codes = [""]
            self.reset = ""

    def code(self, n):
        return self.codes[n % len(self.codes)]


class term:
    """Main"""

    def __init__(self,
                 sensors,
                 add_cr=False,
                 raw=True,
                 color=True,
                 # logfiledir=None,
                 bufsize=65536):

        self.color = termColor()
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
        self.quote_re = None

    def print_header(self, nodes, output=sys.stdout):
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
        for (n, sensor) in enumerate(self.sensors):
            self.threads.append(threading.Thread(
                target=self.reader,
                args=(sensor, self.color.code(n), n)
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

    def reader(self, sensor, color, index):
        """Loop and copy sensor->console.  'sensor' is the sensor device,
        'color' is the string for the current color, 'index' is the current
        device index corresponding to 'sensor'."""

        try:
            while self.alive:
                data = sensor.getVal()
                if data is None:  # this means it has no data to upload.
                    continue

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

                # Upload data
                dataDict = {}
                dataDict["value"] = data
                dataDict["sensorName"] = sensor.sensorName
                for i in outputPlugins:
                    i.outputData(dataDict)

                os.write(sys.stdout.fileno(), data)
        except Exception as e:
            sys.stdout.write(color)
            sys.stdout.flush()
            traceback.print_exc()
            sys.stdout.write(self.color.reset)
            sys.stdout.flush()
            os._exit(1)

    def run(self):
        # Handle SIGINT gracefully
        signal.signal(signal.SIGINT, lambda *args: self.stop())

        # Go
        self.start()
        self.join()

        # Cleanup
        sys.stdout.write(self.color.reset + "\n")

if __name__ == "__main__":
    import argparse
    import re

    formatter = argparse.ArgumentDefaultsHelpFormatter
    description = ("Based on AirPi and terminal.py the program "
                   "logs data from connected sensors."
                   "The outputs are shown in varying colors.")
    parser = argparse.ArgumentParser(description=description,
                                     formatter_class=formatter)

    parser.add_argument("--quiet", "-q", action="store_true",
                        help="Don't print header")

    parser.add_argument("--crlf", "-c", action="store_true",
                        help="Add CR before incoming LF")
    parser.add_argument("--mono", "-m", action="store_true",
                        help="Don't use colors in output")
    parser.add_argument("--bufsize", "-z", metavar="SIZE", type=int,
                        help="Buffer size for reads and writes", default=65536)

    args = parser.parse_args()

    # Load settings.cfg
    if os.path.isfile("settings.cfg"):
        mainConfig = configparser.SafeConfigParser()
        mainConfig.read("settings.cfg")
    else:
        print("Unable to access config file: settings.cfg")

    # Load configuration from various sensors
    if not os.path.isfile('sensors.cfg'):
        print("Unable to access config file: sensors.cfg")
        exit(1)

    # Load sensor configuration
    def get_subclasses(mod, cls):
        for name, obj in inspect.getmembers(mod):
            if hasattr(obj, "__bases__") and cls in obj.__bases__:
                return obj

    sensorConfig = configparser.SafeConfigParser()
    sensorConfig.read('sensors.cfg')
    sensorNames = sensorConfig.sections()

    sensorPlugins = []
    for i in sensorNames:
        try:
            try:
                filename = sensorConfig.get(i, "filename")
            except Exception:
                print("Error: no filename config option found for sensor plugin " + i)
                raise
            try:
                enabled = sensorConfig.getboolean(i, "enabled")
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
                    sensorClass = get_subclasses(mod, sensor.Sensor)
                    if sensorClass == None:
                        raise AttributeError
                except Exception:
                    print("Error: could not find a subclass of sensor.Sensor in module " + filename)
                    raise

                try:
                    reqd = sensorClass.requiredData
                except Exception:
                    reqd = []
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
                        print("Error: Missing required field '" + requiredField + "' for sensor plugin " + i)
                        raise MissingField
                for optionalField in opt:
                    if sensorConfig.has_option(i,optionalField):
                        pluginData[optionalField]=sensorConfig.get(i,optionalField)
                instClass = sensorClass(pluginData)
                sensorPlugins.append(instClass)
                print("Success: Loaded sensor plugin " + i)
        except Exception as e: #add specific exception for missing module
            print("Error: Did not import sensor plugin " + i )
            raise e

    if not os.path.isfile("outputs.cfg"):
        print("Unable to access config file: outputs.cfg")
    outputConfig = configparser.SafeConfigParser()
    outputConfig.read("outputs.cfg")
    outputNames = outputConfig.sections()
    outputPlugins = []

    for i in outputNames:
        try:
            try:
                filename = outputConfig.get(i,"filename")
            except Exception:
                print("Error: no filename config option found for output plugin " + i)
                raise
            try:
                enabled = outputConfig.getboolean(i,"enabled")
            except Exception:
                enabled = True

            #if enabled, load the plugin
            if enabled:
                try:
                    mod = __import__('outputs.'+filename,fromlist=['a']) #Why does this work?
                except Exception:
                    print("Error: could not import output module " + filename)
                    raise

                try:
                    outputClass = get_subclasses(mod,output.Output)
                    if outputClass == None:
                        raise AttributeError
                except Exception:
                    print("Error: could not find a subclass of output.Output in module " + filename)
                    raise
                try:
                    reqd = outputClass.requiredData
                except Exception:
                    reqd = []
                try:
                    opt = outputClass.optionalData
                except Exception:
                    opt = []

                if outputConfig.has_option(i, "async"):
                    async = outputConfig.getbool(i, "async")
                else:
                    async = False

                pluginData = {}

                class MissingField(Exception): pass

                for requiredField in reqd:
                    if outputConfig.has_option(i, requiredField):
                        pluginData[requiredField]=outputConfig.get(i, requiredField)
                    else:
                        print("Error: Missing required field '" + requiredField + "' for output plugin " + i)
                        raise MissingField
                for optionalField in opt:
                    if outputConfig.has_option(i, optionalField):
                        pluginData[optionalField]=outputConfig.get(i, optionalField)
                instClass = outputClass(pluginData)
                instClass.async = async
                outputPlugins.append(instClass)
                print("Success: Loaded output plugin " + i)
        except Exception as e:  # add specific exception for missing module
            print("Error: Did not import output plugin " + i)
            raise e

    app = term(sensorPlugins,
               add_cr=args.crlf,
               color=(os.name == "posix" and not args.mono),
               bufsize=args.bufsize)
    if not args.quiet:
        term.print_header(sensorNames, sys.stderr)

    app.run()
