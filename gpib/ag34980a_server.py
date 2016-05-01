"""
### BEGIN NODE INFO
[info]
name = 34980A
version = 1.0
description = 
instancename = 34980A

[startup]
cmdline = %PYTHON% %FILE%
timeout = 20

[shutdown]
message = 987654321
timeout = 5
### END NODE INFO
"""

import numpy as np
import os
from pyvisa import visa_exceptions
from labrad.server import setting, Signal
from labrad.gpib import GPIBManagedServer, GPIBDeviceWrapper
import labrad.types as T
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet.task import LoopingCall
from influxdb import InfluxDBClient


class Agilent34980AWrapper(GPIBDeviceWrapper):
    def initialize(self):
        pass

    def set_configuration(self, configuration):
        self.configuration = configuration
        for key, value in configuration.__dict__.items():
            setattr(self, key, value)
    
    @inlineCallbacks
    def read_active_channels(self):
        values = []
        active_channels = [address for address, channel in sorted(self.channels.items()) if channel.is_active]
        ac_str = str(active_channels)[1:-1].replace("'", "").replace(' ', '')
        try:
            ans = yield self.query('meas? ' + '(@{})'.format(ac_str))
        except T.Error as e:
            print e.message
            ans = ''
        ans_list = eval('['+ans+']')
        values = [float(a) for a in ans_list]
        returnValue(zip(sorted(self.channels.keys()), values))
    
    @inlineCallbacks
    def measure_channel(self, channel_name):
        for address, channel in self.channels.items():
            if channel.name == channel_name:
                ans = yield self.query(channel.query_string + '(@{})'.format(str(address)))
                print ans
                value = channel.a2v(ans)
                returnValue(value)


class Agilent34980AServer(GPIBManagedServer):
    """Provides basic control for Agilent 34980A Multimeter"""
    deviceWrapper = Agilent34980AWrapper
    
    def __init__(self, configuration_filename):
        self.configuration_filename = configuration_filename
        self.configuration = self.load_configuration()
        if self.configuration:
            GPIBManagedServer.__init__(self)
    
    def load_configuration(self):
        configuration = __import__(self.configuration_filename).ServerConfig()
        for key, value in configuration.__dict__.items():
            setattr(self, key, value)
        return configuration
    
    @inlineCallbacks
    def initServer(self):
        yield GPIBManagedServer.initServer(self)
        self.measurement_loop = LoopingCall(self.measure_active_channels)
        self._load_instruments()
        self.measurement_loop.start(self.measurement_period)

    @setting(9, 'select device by name', name='s', returns='s')    
    def select_device_by_name(self, c, name):
        gpib_device_id = self.instruments[name].gpib_device_id
        yield self.select_device(c, gpib_device_id)
        dev = self.selectedDevice(c)
        dev.set_configuration(self.instruments[name])
        dev.instrument_name = name
        dev.timeout = T.Value(10, 's')
        returnValue(str(self.instruments[name].__dict__))
    
    def _load_instruments(self):
        for name, config in self.instruments.items():
            for key, gpib_device_id in self.list_devices(None):
                if config.gpib_device_id == gpib_device_id:
                    dev = self.devices[key]
                    dev.set_configuration(config)
                    dev.instrument_name = name

    @inlineCallbacks
    def _measure_active_channels(self, dev):
        values = yield dev.read_active_channels()
        influx_client = InfluxDBClient(**dev.db_parameters)
        points = [{"measurement": "DMM", "tags": {"channel": name}, "fields": {"value": value}} for name, value in values]
        influx_client.write_points(points)
        returnValue(values)

    @setting(10, 'measure active channels', returns='*(sv)')
    def measure_active_channels(self, c=None):
        if c is None:
            devs = self.devices.values()
        else:
            devs = [self.selectedDevice(c)]
        values = []
        for dev in devs:
            if hasattr(dev, 'configuration'):
                inst_values = yield self._measure_active_channels(dev)
		print inst_values
                influx_client = InfluxDBClient.from_DSN(os.getenv('INFLUXDBDSN'))
                points = [{"measurement": "DMM", "tags": {"channel": name}, "fields": {"value": value}} for name, value in inst_values]
                influx_client.write_points(points)
                values.append(inst_values)
        returnValue(values)

    @inlineCallbacks
    def _measure_active_channels(self, dev):
        values = yield dev.read_active_channels()
        returnValue(values)

    @inlineCallbacks
    def _update_database(self, db_parameters, values):
        influx_client = yield InfluxDBClient(**db_parameters)
        points = [{"measurement": "DMM", "tags": {"channel": name}, "fields": {"value": value}} for name, value in values]
        yield influx_client.write_points(points)

    @setting(11, 'measure channel', channel_name='s', returns='v')
    def measure_channel(self, c, channel_name):
        dev = self.selectedDevice(c)
        value = yield dev.measure_channel(channel_name)
        returnValue(value)

    @setting(12, 'start measurement loop', period='v')
    def start_measurement_loop(self, c, period=None):
        if period is None:
            period = self.measurement_period
        self.measurement_loop.start(period)

    @setting(13, 'stop measurement loop')
    def stop_measurement_loop(self, c):
        self.measurement_loop.stop()

    @setting(15, 'get system configuration', returns='s')
    def get_system_configuration(self, c):
        conf = self.load_configuration()
        return str(conf)


if __name__ == '__main__':
    configuration_name = '34980a_config'
    __server__ = Agilent34980AServer(configuration_name)
    from labrad import util
    util.runServer(__server__)