from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.web.server import Site, NOT_DONE_YET, Session
from twisted.web.resource import Resource
from twisted.web.static import File
from twisted.internet import reactor, endpoints
from twisted.web.util import redirectTo

from django.template import loader, Template, Context

import json

import sys
sys.path.append('../../client_tools/')
from connection import *

TEMPLATE_DIR = '../../app/templates/'

class DjTemplateResource(Resource):
    def __init__(self, path):
        Resource.__init__(self)
        try:
            self.path = path
            self.template = loader.get_template(template_name=path)
        except Exception as e:
            print e
            print "Error in DjTemplateResource.__init__: " + e.message()
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

class Visualizer(DjTemplateResource):
    path = "base_visualizer_splash.html"

    def __init__(self):
        DjTemplateResource.__init__(self, self.path)

class VisualizerLoad(LabradDjTemplateResource):
    path = "base_visualizer_load.html"

    def __init__(self, cxn=None):
        LabradDjTemplateResource.__init__(self, self.path, cxn)

    def render_GET(self, request):
        self._render_sequences(request)
        return NOT_DONE_YET

    @inlineCallbacks
    def _render_sequences(self, request):
        self.template_context['sequences'] = yield self._get_available_sequences()
        self.template_context['anchors'] = self._get_link_anchors(self.template_context['sequences'])
        request.write(bytes(self.template.render(self.template_context)))
        if not request.finished:
            request.finish()

    @inlineCallbacks
    def _get_available_sequences(self):
        sequence_vault = yield self.cxn.servers['sequencevault']
        ss = yield sequence_vault.get_sequences()

        ret = []
        for s in ss:
            dates = yield sequence_vault.get_dates(s)
            ret.append({'k': s, 'v': list(reversed(dates))})
        returnValue(ret)

    def _get_link_anchors(self, sequences):
        ret = []
        c = 'a'
        for s in sequences:
            if ord(s['k'][0].lower()) >= ord(c):
                ret.append({'k': s['k'][0].lower(), 'v': s['k']})
                c = chr(ord(s['k'][0].lower()) + 1)
        return ret

class VisualizerShow(LabradDjTemplateResource):
    path = "base_visualizer_show.html"

    def __init__(self, cxn=None):
        LabradDjTemplateResource.__init__(self, self.path, cxn)

#class Visualizer(Resource):
#    def __init__(self, cxn):
#        Resource.__init__(self)
#        self.cxn = cxn
#
#    def render_GET(self, request):
#        t = loader.get_template(template_name="base_visualizer_loader.html")
#        return bytes(t.render({'k': 'v'}))
#
#class RunningServers(Resource):
#    def __init__(self, cxn):
#        Resource.__init__(self)
#        self.cxn = cxn
#
#    def render_GET(self, request):
#        self._renderServers(request)
#        return NOT_DONE_YET
#
#    @inlineCallbacks
#    def _renderServers(self, request):
#        t = loader.get_template(template_name="base_home_runningservers.html")
#        d = yield self.get_servers()
#        request.write(bytes(t.render({'labrad_servers': d})))
#        if not request.finished:
#            request.finish()
#
#    @inlineCallbacks
#    def get_servers(self):
#        servers = []
#        labrad_servers = self.cxn.servers
#
#        if labrad_servers.has_key('Manager'):
#            servers.append({'node': 'labradhost', 'name': 'manager', 'status': 'running'})
#        if labrad_servers.has_key('Registry'):
#            servers.append({'node': 'labradhost', 'name': 'registry', 'status': 'running'})
#        for server in labrad_servers.keys():
#            if server.find('node') != -1:
#                ss = yield self.cxn.servers[server].available_servers()
#                for s in ss:
#                    if s in labrad_servers.keys():
#                        servers.append({'node': server, 'name': s, 'status': 'running'})
#                    else:
#                        servers.append({'node': server, 'name': s, 'status': 'not running'})
#        returnValue(servers)
#
#class Other(Resource):
#    def render_GET(self, request):
#        t = loader.get_template(template_name="base_home_other.html")
#        c = Context({'title': 'yo'})
#        return bytes(t.render({}))
