"""
Logs experiment status to InfluxDB. Also manages the shot number.

..
    ### BEGIN NODE INFO
    [info]
    name = logging
    version = 1
    description = server for logging
    instancename = %LABRADNODE%_logging
    [startup]
    cmdline = %PYTHON3% %FILE%
    timeout = 20
    [shutdown]
    message = 987654321
    timeout = 20
    ### END NODE INFO
"""
import sys
from labrad.server import LabradServer, setting, Signal
from labrad.util import getNodeName
import labrad

sys.path.append("../client_tools")
from connection import connection
from twisted.internet.defer import inlineCallbacks, returnValue, Deferred
from twisted.internet import reactor
from twisted.internet.task import LoopingCall
from datetime import datetime
import io
import os, errno
from json import load
import requests
import pytz

try:
    import board
    import adafruit_bmp3xx
except Exception as e:
    print("Could not import BMP390 libraries: %s" % (e))

import influxdb_client
from json import load, loads
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS


BETWEEN_SHOTS_TIME = 60  # how often to log when the experiment is idle (s)

PATHBASE = "K:/data/"


class LoggingServer(LabradServer):
    """Logs messages received from other LabRAD nodes"""

    name = "%LABRADNODE%_logging"

    shot_updated = Signal(314159, "signal: shot_updated", "i")

    def __init__(self):
        self.name = "{}_logging".format(getNodeName())
        self.shot = -1
        self.next_shot = 0
        self.last_time = datetime.now()
        self.logfile = None
        self.freqfile = None
        self.path = None
        super(LoggingServer, self).__init__()

    @inlineCallbacks
    def initServer(self):
        self.set_save_location()
        self.opentime = datetime.now()
        try:
            self.wavemeter = yield self.client.servers["wavemeterlaptop_wavemeter"]

        except Exception as e:
            self.wavemeter = None
            print("Could not connect to wavemeter: %s" % (e))

        try:
            self.labjack = yield self.client.servers["polarkrb_labjack"]

            # Configure FIO2 and FIO3 the LabJack as counter inputs.
            self.labjack.write_name("DIO2_EF_ENABLE", 0)
            self.labjack.write_name("DIO3_EF_ENABLE", 0)
            self.labjack.write_name("DIO2_EF_INDEX", 8)
            self.labjack.write_name("DIO3_EF_INDEX", 8)
            self.labjack.write_name("DIO2_EF_ENABLE", 1)
            self.labjack.write_name("DIO3_EF_ENABLE", 1)
        except Exception as e:
            self.labjack = None
            print("Could not connect to labjack: %s" % (e))

        try:
            i2c = board.I2C()
            self.bmp = adafruit_bmp3xx.BMP3XX_I2C(i2c)
        except Exception as e:
            self.bmp = None
            print("Could not connect to BMP390: %s" % (e))

        with open(
            "C:\\Users\\KRbHyperImage\\Desktop\\labrad_tools\\log\\logging_config.json", "r"
        ) as f:
            self.lasers = load(f)["wavemeter"]["channels"]

        with open(
            "C:\\Users\\KRbHyperImage\\Desktop\\labrad_tools\\log\\secrets.json", "r"
        ) as f:
            config = load(f)
            self.TEMPSTICK_KEY = config["TEMPSTICK_KEY"]
            INFLUXDB_TOKEN = config["INFLUXDB_TOKEN"]
            INFLUXDB_URL = config["INFLUXDB_URL"]

        org = "krb"
        influx_client = influxdb_client.InfluxDBClient(
            url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=org
        )
        self.bucket = "log"
        self.influx_api = influx_client.write_api(write_options=SYNCHRONOUS)

        self.logging_call = LoopingCall(self.log_stuff)
        self.logging_call.start(BETWEEN_SHOTS_TIME, now=True)

        yield None

    @setting(1, message="s", time="t")
    def log(self, c, message, time=None):
        """
        log(self, c, message, time=None)

        Saves a timestamped message to the log file. The name of the sender is also recorded (so the client needs to call :meth:`set_name` first!).

        Args:
            c: A LabRAD context
            message (string): The message to record
            time (datetime.datetime, optional): The time to record. Defaults to None, in which case the current time is used.
        """
        if time is None:
            time = datetime.now()
        if self.shot is None and self.opentime.date() != time.date():
            self.set_save_location()
        logmessage = "%s - %s: %s\n" % (
            time.strftime("%Y-%m-%d %H:%M:%S.%f"),
            c["name"],
            message,
        )
        print(logmessage)
        self.logfile.write(logmessage)
        self.logfile.flush()

    @setting(2, shot="i")
    def set_shot(self, c, shot=None):
        """
        set_shot(self, c, shot=None)

        Sets the number of the shot to record, which determines the folder in which data is saved. The shot number is reset daily. If the shot number is `None`, the experiment is considered idle. This means files are stored in the day's folder on the dataserver. The wavemeter is also set to log at a lower rate when the experiment is idle.

        Args:
            c: A LabRAD context (not used)
            shot (int, optional): The number of the shot to record. Defaults to None, which sets the program to log the idle experiment.
        """
        self.shot = shot
        self.shot_updated(shot if shot is not None else -1)
        self.set_save_location()
        try:
            if self.logging_call.running:
                self.logging_call.stop()
        except Exception as e:
            print("Could not stop looping call for logging: %s" % (e))
        # try:
        if shot is None:
            self.logging_call.start(BETWEEN_SHOTS_TIME)
        else:
            # pass
            # run the logging call once after 10 seconds
            reactor.callLater(7, self.logging_call)
        # except Exception as e:
        #     print("Could not start looping call for wavemeter: %s" % (e))

    @setting(3, returns="i")
    def get_next_shot(self, c):
        """
        get_next_shot(self, c)

        Determines the number for the next shot based on the highest numbered directory in the current day's dataserver folder.

        Args:
            c: A LabRAD context (not used)

        Returns:
            int: the number for the next shot
        """
        currtime = datetime.now()

        if currtime.date() != self.last_time.date():
            self.next_shot = 0
        else:
            self.path = PATHBASE + "%s/shots/" % (currtime.strftime("%Y/%m/%Y%m%d"))
            # if the directory doesn't exist, create it
            try:
                os.makedirs(self.path)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise
            dirlist = []
            for d in os.listdir(self.path):
                try:
                    dirlist.append(int(d))
                except:
                    dirlist.append(-1)
            self.next_shot = max(dirlist) + 1
        self.last_time = currtime

        return self.next_shot

    @setting(4, name="s")
    def set_name(self, c, name):
        """
        set_name(self, c, name)

        Sets the name of the client's connection. The name is entered in the log when messages are sent, so this function must be called before :meth:`log` is run.

        Args:
            c: A LabRAD context
            name (string): The name of the client's connection
        """
        print("Setting name of client %d to %s" % (c.ID[0], name))
        c["name"] = name

    @setting(5, returns="s")
    def get_path(self, c, name):
        """
        get_path(self, c)

        Returns the path where the current shot's data is saved.

        Args:
            c: A LabRAD context
        """
        return self.path

    @setting(6, returns="i")
    def get_shot(self, c, name):
        """
        get_shot(self, c)

        Returns the current shot. If the current shot is None, return -1.

        Args:
            c: A LabRAD context
        """
        if self.shot is not None:
            return self.shot
        else:
            return -1

    def set_save_location(self):
        """
        Sets the save location based on the current time and shot number.
        """
        now = datetime.now()
        self.opentime = now
        if isinstance(self.logfile, io.IOBase) and not self.logfile.closed:
            self.logfile.close()
        if isinstance(self.freqfile, io.IOBase) and not self.freqfile.closed:
            self.freqfile.close()
        if self.shot is None:
            # save to a log file in the directory on the data server defined by the date; make directories if necessary
            self.path = PATHBASE + "%s/" % (now.strftime("%Y/%m/%Y%m%d"))
        else:
            # save to a log file in a directory defined by the date and the shot number; make directories if necessary
            self.path = PATHBASE + "%s/shots/%d/" % (
                now.strftime("%Y/%m/%Y%m%d"),
                self.shot,
            )
        fname = self.path + "log.txt"
        ffname = self.path + "freqs.txt"

        try:
            os.makedirs(self.path)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

        self.logfile = open(fname, "a+")
        self.freqfile = open(ffname, "a+")
        print("Opening log file %s" % (fname))

    def get_tempstick(self):
        try:
            url = "https://tempstickapi.com/api/v1/sensors/all"
            headers = {"X-API-KEY": self.TEMPSTICK_KEY}
            sensors = requests.get(url, headers=headers).json()["data"]["items"]
            data = {}
            for s in sensors:
                data[s["sensor_name"]] = {
                    "temp": s["last_temp"],
                    "humidity": s["last_humidity"],
                    "last_checkin": s["last_checkin"],
                }
            return data
        except Exception as e:
            print("Could not read tempstick: %s" % (e))
            return None

    @inlineCallbacks
    def log_stuff(self):
        now = datetime.now(pytz.timezone("US/Mountain"))

        # write to influxdb
        if self.shot is not None:
            try:
                p = Point("shot").field("shot", self.shot).time(now, WritePrecision.S)
                self.influx_api.write(self.bucket, "krb", p)
            except Exception as e:
                print("Could not write shot data to influxdb: %s" % (e))

        # write temperature data
        tempstick = self.get_tempstick()
        for sensor in tempstick:
            try:
                temp = float(tempstick[sensor]["temp"])
                humidity = float(tempstick[sensor]["humidity"])
                p = (
                    Point("temperature")
                    .tag("sensor", sensor)
                    .field("temp", temp)
                    .field("humidity", humidity)
                    .time(now, WritePrecision.S)
                )
                self.influx_api.write(self.bucket, "krb", p)
            except Exception as e:
                print("Could not write temperature data to influxdb: %s" % (e))

        # write labjack data
        try:
            RbMOT = yield self.labjack.read_name("AIN0")
            p = (
                Point("labjack")
                .tag("channel", "RbMOT")
                .tag("unit", "V")
                .field("value", RbMOT)
                .time(now, WritePrecision.S)
            )
            self.influx_api.write(self.bucket, "krb", p)
        except Exception as e:
            print("Could not write RbMOT data to influxdb: %s" % (e))
        try:
            KMOT = yield self.labjack.read_name("AIN1")
            p = (
                Point("labjack")
                .tag("channel", "KMOT")
                .tag("unit", "V")
                .field("value", KMOT)
                .time(now, WritePrecision.S)
            )
            self.influx_api.write(self.bucket, "krb", p)
        except Exception as e:
            print("Could not write KMOT data to influxdb: %s" % (e))
        try:
            waterPressure = yield self.labjack.read_name("AIN2")
            waterPressure *= 15.0  # 15 PSI/V
            p = (
                Point("labjack")
                .tag("channel", "waterPressure")
                .tag("unit", "PSI")
                .field("value", waterPressure)
                .time(now, WritePrecision.S)
            )
            self.influx_api.write(self.bucket, "krb", p)
        except Exception as e:
            print("Could not write waterPressure data to influxdb: %s" % (e))
        try:
            leak_sensor_0 = yield self.labjack.read_name("DIO2_EF_READ_A")
            p = (
                Point("labjack")
                .tag("channel", "leak_sensor_0")
                .field("value", leak_sensor_0)
                .time(now, WritePrecision.S)
            )
            self.influx_api.write(self.bucket, "krb", p)
        except Exception as e:
            print("Could not write leak_sensor_0 data to influxdb: %s" % (e))
        try:
            leak_sensor_1 = yield self.labjack.read_name("DIO3_EF_READ_A")
            p = (
                Point("labjack")
                .tag("channel", "leak_sensor_1")
                .field("value", leak_sensor_1)
                .time(now, WritePrecision.S)
            )
            self.influx_api.write(self.bucket, "krb", p)
        except Exception as e:
            print("Could not write leak_sensor_1 data to influxdb: %s" % (e))
        try:
            manifold_v = yield self.labjack.read_name("AIN3")
            manifold_temp_C = (manifold_v * 100.0 - 32.0) * 5.0 / 9.0
            p = (
                Point("labjack")
                .tag("channel", "Water Manifold")
                .tag("unit", "C")
                .field("value", manifold_temp_C)
                .time(now, WritePrecision.S)
            )
            self.influx_api.write(self.bucket, "krb", p)
        except Exception as e:
            print("Could not write manifold_temp data to influxdb: %s" % (e))
        try:
            table_valve_ctrl = yield self.labjack.read_name("AIN4")
            p = (
                Point("labjack")
                .tag("channel", "table_valve_ctrl")
                .tag("unit", "V")
                .field("value", table_valve_ctrl)
                .time(now, WritePrecision.S)
            )
            self.influx_api.write(self.bucket, "krb", p)
        except Exception as e:
            print("Could not write table_valve_ctrl data to influxdb: %s" % (e))
        try:
            bias_flow_rate = yield self.labjack.read_name("AIN5")
            bias_flow_rate *= 0.6 / 10.0  # 0.6 GPM/10V
            p = (
                Point("labjack")
                .tag("channel", "bias_flow_rate")
                .tag("unit", "GPM")
                .field("value", bias_flow_rate)
                .time(now, WritePrecision.S)
            )
            self.influx_api.write(self.bucket, "krb", p)
        except Exception as e:
            print("Could not write bias coil flow rate data to influxdb: %s" % (e))
        try:
            mot_fluorescence = yield self.labjack.read_name("AIN6")
            p = (
                Point("labjack")
                .tag("channel", "mot_fluorescence")
                .tag("unit", "V")
                .field("value", mot_fluorescence)
                .time(now, WritePrecision.S)
            )
            self.influx_api.write(self.bucket, "krb", p)
        except Exception as e:
            print("Could not write mot_fluorescence data to influxdb: %s" % (e))

        # write BMP390 data
        try:
            temp = self.bmp.temperature
            pressure = self.bmp.pressure
            p1 = (
                Point("bmp390")
                .tag("channel", "temp")
                .tag("unit", "C")
                .field("value", temp)
                .time(now, WritePrecision.S)
            )
            p2 = (
                Point("bmp390")
                .tag("channel", "pressure")
                .tag("unit", "hPa")
                .field("value", pressure)
                .time(now, WritePrecision.S)
            )
            self.influx_api.write(self.bucket, "krb", [p1, p2])
        except Exception as e:
            print("Could not write BMP390 data to influxdb: %s" % (e))

        # write wavemeter data
        try:
            wavelengths = yield self.wavemeter.get_wavelengths()
            wavelens = loads(loads(wavelengths))
            freqs = {}
            for i, l in enumerate(self.lasers):
                if l["i"] < 8:
                    wl = 299792.458 / wavelens["wavelengths"][l["i"]]
                    freqs[l["label"]] = {"freq": wl, "unit": "THz"}
                else:
                    wl = wavelens["freq"]
                    freqs[l["label"]] = {"freq": wl, "unit": "MHz"}
            for laser in freqs:
                freq = freqs[laser]["freq"]
                p = (
                    Point("wavemeter")
                    .tag("laser", laser)
                    .field("freq", freq)
                    .time(now, WritePrecision.S)
                )
                self.influx_api.write(self.bucket, "krb", p)
        except Exception as e:
            print("Could not write wavemeter data to influxdb: %s" % (e))

        print("Logged at %s" % (now.strftime("%Y-%m-%d %H:%M:%S.%f")))


if __name__ == "__main__":
    from labrad import util

    util.runServer(LoggingServer())
