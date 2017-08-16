import json
import os
from influxdb import InfluxDBClient
from labrad.wrappers import connectAsync
from twisted.internet.defer import inlineCallbacks
from twisted.internet.reactor import callInThread

from conductor_device.conductor_parameter import ConductorParameter

def to_float(x):
    try:
        return float(x)
    except:
        return 0.

class Client(ConductorParameter):
    priority = 1
    @inlineCallbacks
    def initialize(self):
        self.cxn = yield connectAsync()
        self.counter = 0
        self.dbclient = InfluxDBClient.from_DSN(os.getenv('INFLUXDBDSN'))
    
    @inlineCallbacks
    def update(self):
        self.counter += 1
        if self.counter >= 100:
            self.counter = 0
            parameters_json = yield self.cxn.conductor.get_parameter_values()
            parameters = json.loads(parameters_json)
        
            to_db = [
                {
                    "measurement": "experiment parameters",
                    "tags": {"device": device_name, "parameter": p},
                    "fields": {"value": to_float(v)},
                } for device_name, device in parameters.items() 
                  for p, v in device.items()
            ]
        
            callInThread(self.dbclient.write_points, to_db)
