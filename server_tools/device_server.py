import re
import json
import types
import os

from twisted.internet.defer import returnValue, inlineCallbacks
from labrad.server import LabradServer, setting

from decorators import quickSetting


def underscore(name):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z])([A-Z])', r'\1_\2', s1).lower()

def add_quick_setting(srv, ID, setting_name, arg_type):
    def setting(self, c, arg=None):
        pass
    setting.__name__ = str(setting_name)
    setting.__doc__ = "get or change {} ".format(setting_name)
    method = types.MethodType(setting, srv)
    qs = quickSetting(ID, arg_type)(method)
    setattr(srv, setting_name, qs)

def get_device_wrapper(device_config):
    device_type = device_config['device_type']
    _device_type = underscore(device_type)
    module_path = 'devices.{}'.format(_device_type)
    if os.path.isdir(_device_type):
        module_path += _device_type
    module = __import__(module_path, fromlist=[device_type])
    print module.__dict__.keys()
    return getattr(module, device_type)

def get_connection_wrapper(device):
    module_path = 'server_tools.connections.{}_connection'.format(device.connection_type.lower())
    module = __import__(module_path, fromlist=[device.connection_type+'Connection'], level=1)
    return getattr(module, device.connection_type+'Connection')

class DeviceWrapper(object):
    def __init__(self, config={}):
        for key, value in config.items():
            setattr(self, key, value)
        self.connection_name = self.servername + ' - ' + self.address

    @inlineCallbacks 
    def initialize(self):
        yield None


class DeviceServer(LabradServer):
    def __init__(self, config_path='./config.json'):
        LabradServer.__init__(self)
        self.devices = {}
        self.open_connections = {}
        self.quick_settings = []

        self.load_config(config_path)
#        for i, (setting, arg_type) in enumerate(self.quick_settings):
#            add_quick_setting(self, 10 + i, setting, arg_type)

    def load_config(self, path=None):
        self.config = lambda: None
        if path is not None:
            self.config_path = path
        with open(self.config_path, 'r') as infile:
            config = json.load(infile)
            for key, value in config.items():
                setattr(self.config, key, value)

    @inlineCallbacks
    def initServer(self):
        for name, config in self.config.devices.items():
            yield self.initialize_device(name, config)

    @inlineCallbacks 
    def initialize_device(self, name, config):
        device_wrapper = get_device_wrapper(config)
        device_wrapper.name = name
        device = device_wrapper(config)
        try: 
            if device.connection_name not in self.open_connections:
                yield self.init_connection(device)
            device.connection = self.open_connections[device.connection_name]
            self.devices[name] = device
            yield device.initialize()
        except Exception, e:
            print e
            print 'could not initialize device {}'.format(name)
            print 'removing {} from available devices'.format(name)
            self.devices.pop(name)
    
    @inlineCallbacks
    def init_connection(self, device):
        connection = get_connection_wrapper(device)()
        yield connection.initialize(device)
        print 'connection opened: {} - {}'.format(device.servername, device.address)
        self.open_connections[device.connection_name] = connection

    def get_device(self, c):
        name = c.get('name')
        if name is None:
            raise Exception('select a device first')
        return self.devices[name]

    @setting(0, returns='*s')
    def get_device_list(self, c):
        return self.devices.keys()
    
    @setting(1, name='s', returns=['s', ''])
    def select_device(self, c, name):
        if name not in self.devices.keys():
            try: 
                yield self.reload_config(c, name)
            except:
                message = '{} is not the name of a configured device'.format(
                           name)
                raise Exception(message)
                returnValue(None)
        c['name'] = name
        device = self.get_device(c)
        returnValue(json.dumps(device.__dict__, default=lambda x: None))
    
    @setting(3, returns='b')
    def reinit_connection(self, c):
        device = self.get_device(c)
        yield self.init_connection(device)
        device.connection = self.open_connections[device.connection_name]
        returnValue(True)

    @setting(4)
    def send_update(self, c):
        device = self.get_device(c)
        update = {c['name']: {p: getattr(device, p) 
                  for p in device.update_parameters}}
        yield self.update(json.dumps(update))

    @setting(5, names=['*s', 's'])
    def reload_config(self, c, names=None):
        self.load_config()
        if names is None:
            names = self.config.devices
        elif type(names).__name__ != 'list':
            names = [names]
        for name in names:
            device = self.config.devices.get(name)
            if device:
                yield self.initialize_device(name, device)
