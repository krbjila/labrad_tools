from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.web.server import Site, NOT_DONE_YET, Session
from twisted.web.resource import Resource
from twisted.web.static import File
from twisted.internet import reactor, endpoints
from twisted.web.util import redirectTo

from zope.interface import Interface, Attribute, implementer
from twisted.python.components import registerAdapter

from django.template import loader, Template, Context

import json

import sys
sys.path.append('../../client_tools/')
from connection import *

sys.path.append('../../sequencer/devices/lib/')
from analog_ramps import RampMaker as analogRampMaker
from ad5791_ramps import RampMaker as stableRampMaker

TEMPLATE_DIR = '../../app/templates/'
        
DIGITAL_CHANNELS = [chr(x) for x in range(ord("A"), ord("H") + 1)]

TIME_PRECISION = 9 # 1 ns precision; expt resolution is only 100 ns, but use this to avoid rounding errors

class IExperiment(Interface):
    value = Attribute("A tuple (str, str, int) value that holds the experiment name, date, and version.")

@implementer(IExperiment)
class Experiment(object):
    def __init__(self, session):
        self.value = ("", "", 0)

registerAdapter(Experiment, Session, IExperiment)

def getSessionExperiment(request):
    session = request.getSession()
    return IExperiment(session).value

def setSessionExperiment(request, experiment, date, version):
    session = request.getSession()
    IExperiment(session).value = (experiment, date, version)

class DjTemplateResource(Resource):
    def __init__(self, path):
        Resource.__init__(self)
        try:
            self.path = path
            self.template = loader.get_template(template_name=path)
        except Exception as e:
            if isinstance(e, (str, unicode)):
                print "Error in DjTemplateResource.__init__: " + e
            else:
                print "Error in DjTemplateResource.__init__: " + e.message
        self.template_context = {}

    def render_GET(self, request):
        return bytes(self.template.render(self.template_context))

class LabradDjTemplateResource(DjTemplateResource):
    def __init__(self, path, cxn):
        DjTemplateResource.__init__(self, path)
        self.cxn = cxn

class KRbRoot(Resource):
    def render_GET(self, request):
        return redirectTo("/krbtools/home", request)

class KRbHome(DjTemplateResource):
    path = "base_home_splash.html"

    def __init__(self):
        DjTemplateResource.__init__(self, self.path)

class Dashboard(LabradDjTemplateResource):
    path = "base_home_dashboard.html"
    ID_start = 123123
    ID_stop = 123124
    ID_par_removed = 123125
    ID_pars_refreshed = 123126

    def __init__(self, cxn=None):
        LabradDjTemplateResource.__init__(self, self.path, cxn)
        self.connect()

    @inlineCallbacks
    def connect(self):
        self.cxn = connection()
        yield self.cxn.connect()

        try:
            server = yield self.cxn.get_server('conductor')

            # Connect to experiment_started signal from conductor
            yield server.signal__experiment_started(self.ID_start)
            yield server.addListener(listener = self.started, source = None, ID = self.ID_start)
    
            # Connect to experiment_stopped signal from Conductor
            yield server.signal__experiment_stopped(self.ID_stop)
            yield server.addListener(listener = self.ready, source = None, ID = self.ID_stop)
     
            # Connect to parameter_removed signal from Conductor
            yield server.signal__parameter_removed(self.ID_par_removed)
            yield server.addListener(listener = self.parameter_removed, source = None, ID = self.ID_par_removed)
    
            yield server.signal__parameters_refreshed(self.ID_pars_refreshed)
            yield server.addListener(listener=self.parameters_refreshed, source=None, ID = self.ID_pars_refreshed)

            self.ready(None, None)

            yield self.cxn.add_on_disconnect('conductor', self.server_stopped)
            yield self.cxn.add_on_connect('conductor', self.server_started)

        except Exception as e:
            self.server_stopped()
            print e
            
    def started(self, c, signal):
        self.template_context['status'] = 'running'

    def ready(self, c, signal):
        self.template_context['status'] = 'ready'

    def parameter_removed(self, c, signal):
        self.template_context['status'] = 'warning'
    
    def parameters_refreshed(self, c, signal):
        self.template_context['status'] = 'ready'

    def server_stopped(self):
        self.template_context['status'] = 'off'

    def server_started(self):
        self.template_context['status'] = 'ready'

    def render_GET(self, request):
        self._renderParameterValues(request)
        return NOT_DONE_YET

    @inlineCallbacks
    def _renderParameterValues(self, request):
        if self.template_context['status'] == 'off':
            yield self.connect()

        self.template_context['pvs'] = yield self.get_values()
        request.write(bytes(self.template.render(self.template_context)))
        if not request.finished:
            request.finish()

    @inlineCallbacks
    def get_values(self):
        try:
            server = yield self.cxn.get_server('conductor')
            pv_s = yield server.get_parameter_values()
            
            pv = json.loads(pv_s)
            ret = []

            # Sort everything alphabetically for convenience
            for k in sorted(pv.keys()):
                v = []
                if k == 'sequencer':
                    index = 1
                else:
                    index = 0

                for kk in sorted(pv[k].keys(), key=lambda x: x[index].capitalize()):
                    v.append({'k': kk, 'v': pv[k][kk]})
                ret.append({'k': k, 'v': v})
            returnValue(ret)
        except Exception as e:
            print e
            returnValue({})

class RunningServers(LabradDjTemplateResource):
    path = "base_home_runningservers.html"

    def __init__(self, cxn=None):
        LabradDjTemplateResource.__init__(self, self.path, cxn)

    def render_GET(self, request):
        self._renderServers(request)
        return NOT_DONE_YET

    @inlineCallbacks
    def _renderServers(self, request):
        self.template_context['labrad_servers'] = yield self.get_servers()
        request.write(bytes(self.template.render(self.template_context)))
        if not request.finished:
            request.finish()

    @inlineCallbacks
    def get_servers(self):
        servers = []
        labrad_servers = self.cxn.servers

        if labrad_servers.has_key('Manager'):
            servers.append({'node': 'labradhost', 'name': 'manager', 'status': 'running'})
        if labrad_servers.has_key('Registry'):
            servers.append({'node': 'labradhost', 'name': 'registry', 'status': 'running'})
        for server in labrad_servers.keys():
            if server.find('node') != -1:
                ss = yield self.cxn.servers[server].available_servers()
                for s in ss:
                    if s in labrad_servers.keys():
                        servers.append({'node': server, 'name': s, 'status': 'running'})
                    else:
                        servers.append({'node': server, 'name': s, 'status': 'not running'})
        returnValue(servers)

class Other(LabradDjTemplateResource):
    path = "base_home_other.html"

    def __init__(self, cxn=None):
        LabradDjTemplateResource.__init__(self, self.path, cxn)

class Visualizer(LabradDjTemplateResource):
    path = "base_visualizer.html"

    def __init__(self, cxn):
        LabradDjTemplateResource.__init__(self, self.path, cxn)

    def render_GET(self, request):
        self._render(request)
        return NOT_DONE_YET

    @inlineCallbacks
    def _render(self, request):
        channels = yield self.get_channels()
        self.template_context = self.get_channel_dict(channels)
        request.write(bytes(self.template.render(self.template_context)))

        if not request.finished:
            request.finish()

    @inlineCallbacks
    def get_channels(self):
        sequencer = yield self.cxn['sequencer']
        channels = yield sequencer.get_channels()
        returnValue(json.loads(channels))

    def get_channel_dict(self, channels):
        out = {}
        for k,v in channels.items():
            if v['channel_type'] not in out:
                out[v['channel_type']] = [v]
            else:
                out[v['channel_type']].append(v)
        
        ret = {}
        for k,v in out.items():
            d = {}
            for x in v:
                if x['loc'][0] in d:
                    d[x['loc'][0]].append(x)
                else:
                    d[x['loc'][0]] = [x]
            arr = [{'device': kk, 'channels': sorted(vv, key=lambda x: x['loc'])} for kk,vv in d.items()]
            ret[k] = sorted(arr, key=lambda x: x['device'])
        return ret