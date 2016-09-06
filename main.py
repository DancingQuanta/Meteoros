#!/usr/bin/python

# Andrew Tolmie <earat@leeds.ac.uk>

# A program that logs data from sensors and pass them to output plugins.
# Each sensor is a defined in a plugin each and is selected in sensors.cfg
# A output plugin works on each sensor's data.

import sys
import os
import threading
import traceback
import signal
import configparser
import inspect
from sensors import Sensor
from outputs import Output


def get_subclasses(mod, cls):
    for name, obj in inspect.getmembers(mod):
        if hasattr(obj, "__bases__") and cls in obj.__bases__:
            return obj


def load_plugins(config, type):
    # Load configuration from various plugsin of a type
    if not os.path.isfile(config):
        print("Unable to access config file: %s" % (config))
        exit(1)

    # Get directory of running script
    cwd = os.path.abspath(os.path.dirname(__file__))

    # Get directory of type plugins
    type_path = os.path.dirname(inspect.getfile(type))
    type_path = os.path.relpath(type_path, cwd)

    plugin_config = configparser.SafeConfigParser()
    plugin_config.read(config)
    names = plugin_config.sections()

    plugins = []
    for i in names:
        try:
            try:
                filename = plugin_config.get(i, "filename")
            except Exception:
                msg = ("Error: no filename config option found for "
                       "%s plugin %s" % (type.__name__, i))
                print(msg)
                raise
            try:
                enabled = plugin_config.getboolean(i, "enabled")
            except Exception:
                enabled = True

            # If enabled, load the plugin
            if enabled:
                try:
                    path = type_path + '.' + filename
                    mod = __import__(path, fromlist=['a'])  # Why does this work?
                except Exception:
                    msg = ("Error: could not import %s module "
                           "%s" % (type.__name__, filename))
                    print(msg)
                    raise

                try:
                    plugin_class = get_subclasses(mod, type)
                    if plugin_class is None:
                        raise AttributeError
                except Exception:
                    msg = ("Error: could not find a subclass of %s "
                           "in module %s" % (type.__name__, filename))
                    print(msg)
                    raise

                try:
                    reqd = plugin_class.requiredData
                except Exception:
                    reqd = []
                try:
                    opt = plugin_class.optionalData
                except Exception:
                    opt = []

                plugin_data = {}

                class MissingField(Exception): pass

                for requiredField in reqd:
                    if plugin_config.has_option(i, requiredField):
                        plugin_data[requiredField] = plugin_config.get(i, requiredField)
                    else:
                        msg = ("Error: Missing required field '%s' for %s"
                               "plugin %s" % (requiredField, type.__name__, i))
                        print(msg)
                        raise MissingField
                for optionalField in opt:
                    if plugin_config.has_option(i, optionalField):
                        plugin_data[optionalField] = plugin_config.get(i, optionalField)

                instClass = plugin_class(plugin_data)
                plugins.append(instClass)
                print("Success: Loaded %s plugin %s" % (type.__name__, i))
        except Exception as e:  # Add specific exception for missing module
            print("Error: Did not import %s plugin %s" % (type.__name__, i))
            raise e
    return plugins, names


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
                 outputs,
                 add_cr=False,
                 raw=True,
                 color=True,
                 # logfiledir=None,
                 bufsize=65536):

        self.color = termColor()
        if color:
            self.color.setup(len(sensors))

        self.sensors = sensors
        self.outputs = outputs
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
                for i in self.outputs:
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

    # Load sensor plugins
    sensorPlugins, sensorNames = load_plugins("sensors.cfg", Sensor)

    # Load output plugins
    outputPlugins, outputNames = load_plugins("outputs.cfg", Output)

    app = term(sensorPlugins,
               outputPlugins,
               add_cr=args.crlf,
               color=(os.name == "posix" and not args.mono),
               bufsize=args.bufsize)
    if not args.quiet:
        app.print_header(sensorNames, sys.stderr)

    app.run()
