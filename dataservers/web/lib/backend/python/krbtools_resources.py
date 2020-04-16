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

class Visualizer(DjTemplateResource):
    path = "base_visualizer_splash.html"

    def __init__(self):
        DjTemplateResource.__init__(self, self.path)

#class VisualizerLoad(LabradDjTemplateResource):
#    path = "base_visualizer_load.html"
#
#    def __init__(self, cxn=None):
#        LabradDjTemplateResource.__init__(self, self.path, cxn)
#
#    def render_GET(self, request):
#        session = request.getSession()
#        print IExperiment(session).value
#
#        self._render(request)
#        return NOT_DONE_YET
#
#    @inlineCallbacks
#    def _render(self, request):
#        versions = yield self._get_experiments()
#        if all(k in request.args.keys() for k in ['experiment', 'date', 'version']):
#            expt = request.args['experiment'][0]
#            date = request.args['date'][0]
#            v = int(request.args['version'][0])
#
#            if v in versions[expt][date]:
#                session = request.getSession()
#                se = IExperiment(session)
#                se.value = (expt, date, v)
#
#                ret = yield self._get_experiment_parameters(expt, date, v)
#                sequences = ret['experiment']['sequencer']['sequence'][0]
#                durations = yield self._get_sequence_durations(sequences, date)
#                arr = [{'name': s, 'date': d, 'duration': dd} for s, d, dd in zip(sequences, ret['dates'], durations)] 
#                request.write(json.dumps(arr))
#        elif 'all' in request.args:
#            if request.args['all'][0] == 'true':
#                r = {}
#                r['sequences'] = yield self._get_available_sequences()
#                r['experiments'] = versions
#                request.write(json.dumps(r))
#        else:
#            self.template_context['experiments'] = versions
#            request.write(bytes(self.template.render(self.template_context)))
#        if not request.finished:
#            request.finish()
#
#    @inlineCallbacks
#    def _get_sequence_durations(self, sequences, date):
#        sequence_vault = yield self.cxn.servers['sequencevault']
#        durations = yield sequence_vault.get_sequence_durations(sequences, date)
#        returnValue(json.loads(durations))
#
#    @inlineCallbacks
#    def _get_experiment_parameters(self, experiment, date, version):
#        experiment_vault = yield self.cxn.servers['experimentvault']
#        expt = yield experiment_vault.get_experiment_data(experiment, date, version)
#        returnValue(json.loads(expt))
#
#    @inlineCallbacks
#    def _get_available_sequences(self):
#        sequence_vault = yield self.cxn.servers['sequencevault']
#        ss = yield sequence_vault.get_sequences()
#
#        ret = []
#        for s in ss:
#            dates = yield sequence_vault.get_dates(s)
#            ret.append({'k': s, 'v': list(reversed(dates))})
#        returnValue(ret)
#
#    def _get_link_anchors(self, sequences):
#        ret = []
#        c = 'a'
#        for s in sequences:
#            if ord(s['k'][0].lower()) >= ord(c):
#                ret.append({'k': s['k'][0].lower(), 'v': s['k']})
#                c = chr(ord(s['k'][0].lower()) + 1)
#        return ret
#
#    @inlineCallbacks
#    def _get_experiments(self):
#        experiment_vault = yield self.cxn.servers['experimentvault']
#        expts = yield experiment_vault.get_available_experiments()
#        returnValue(json.loads(expts))


class VisualizerLoadExperiments(Resource):
    def __init__(self, cxn):
        Resource.__init__(self)
        self.cxn = cxn
        self.template_context = {}

    def render_GET(self, request):
        session = request.getSession()
        self._render_sequences(request)
        return NOT_DONE_YET

    @inlineCallbacks
    def _render_sequences(self, request):
        (expts, dates, versions) = yield self._get_experiments()
        if all(k in request.args.keys() for k in ['experiment', 'date', 'version']):
            expt = request.args['experiment'][0]
            date = request.args['date'][0]
            v = int(request.args['version'][0])

            if v in versions[expt][date]:
                setSessionExperiment(request, expt, date, v)

                ret = yield self._get_experiment_parameters(expt, date, v)
                sequences = ret['experiment']['sequencer']['sequence'][0]
                durations = yield self._get_sequence_durations(sequences, date)
                arr = [{'name': s, 'date': d, 'duration': dd} for s, d, dd in zip(sequences, ret['dates'], durations)] 
                request.write(json.dumps(arr))
        else:
            self.template_context['experiments'] = versions

            ses = getSessionExperiment(request)
            self.template_context['session'] = ses
            request.write(json.dumps(self.template_context))
        if not request.finished:
            request.finish()

    @inlineCallbacks
    def _get_sequence_durations(self, sequences, date):
        sequence_vault = yield self.cxn.servers['sequencevault']
        durations = yield sequence_vault.get_sequence_durations(sequences, date)
        returnValue(json.loads(durations))

    @inlineCallbacks
    def _get_experiment_parameters(self, experiment, date, version):
        experiment_vault = yield self.cxn.servers['experimentvault']
        expt = yield experiment_vault.get_experiment_data(experiment, date, version)
        returnValue(json.loads(expt))

    @inlineCallbacks
    def _get_experiments(self):
        experiment_vault = yield self.cxn.servers['experimentvault']
        expts = yield experiment_vault.get_available_experiments()
        expts = json.loads(expts)

        e_list = sorted(expts.keys(), key=lambda x: x[0].lower())
        e_dates = {k: sorted(v.keys()) for k,v in expts.items()}
        e_versions = expts
        returnValue((e_list, e_dates, e_versions))

class VisualizerLoad(LabradDjTemplateResource):
    path = "base_visualizer_load.html"

    def __init__(self, cxn=None):
        LabradDjTemplateResource.__init__(self, self.path, cxn)

class VisualizerSequence(Resource):
    def __init__(self, cxn=None):
        Resource.__init__(self)
        self.cxn = cxn

    def render_GET(self, request):
        self._render(request)
        return NOT_DONE_YET

    @inlineCallbacks
    def _render(self, request):
        try:
            experiment = request.args['experiment'][0]
            date = request.args['date'][0]
            version = int(request.args['version'][0])

            experiment_vault = yield self.cxn.servers['experimentvault']
            data = yield experiment_vault.get_experiment_data(experiment, date, version)
            data = json.loads(data)
            sequence_list = data['experiment']['sequencer']['sequence'][0]

            sequence_vault = yield self.cxn.servers['sequencevault']

            sequence = yield sequence_vault.get_joined_sequence(sequence_list, date)
            sequence = json.loads(sequence)

            substituted_sequence = yield sequence_vault.get_substituted_sequence(sequence_list, date)
            substituted_sequence = json.loads(substituted_sequence)

            plottable = yield self.get_plottable(substituted_sequence)

            out = {'meta': sequence['meta'], 'plottable': plottable}
            request.write(bytes(json.dumps(out)))
        except Exception as e:
            print e
        if not request.finished:
            request.finish()

    @inlineCallbacks
    def get_plottable(self, sequence):
        sequencer = yield self.cxn.servers['sequencer']
        channels = yield sequencer.get_channels()
        channels = json.loads(channels)
        returnValue(self.sequence_to_plottable(channels, sequence))

    def map_channel_names(self, channels):
        lookup = {}
        for k,v in channels.items():
            lookup[v['loc']] = k
        return lookup

    def sequence_to_plottable(self, channels, sequence):
        lookup = self.map_channel_names(channels)

        out = {}
        for k,v in sequence.items():
            kk = lookup[k.split('@')[-1]]

            if channels[kk]['channel_type'] == 'digital':
                times = [0]
                values = [0]

                for step in v:
                    # Needed to make square edges on waveform
                    if step['out'] != values[-1]:
                        times.append(round(times[-1], TIME_PRECISION))
                        values.append(step['out'])

                    times.append(round(times[-1] + step['dt'], TIME_PRECISION))
                    values.append(step['out'])

                if channels[kk]['invert']:
                    values = [-1.0*(vv-1.0) for vv in values]
                out[k] = zip(times, values)
            else:
                if channels[kk]['board_name'] != 'S':
                    r = analogRampMaker(v)
                    s = r.get_programmable()

                    times = [0]
                    values = [0]
                    for step in s:
                        times.append(round(times[-1] + step['dt'], TIME_PRECISION))
                        values.append(values[-1] + step['dv'])
                    out[k] = zip(times, values) 
                else:
                    r = stableRampMaker(v)
                    s = r.get_programmable()

                    times = [0]
                    values = [0]
                    for step in s:
                        times.append(round(times[-1] + step['dt'], TIME_PRECISION))
                        values.append(step['v'])
                    out[k] = zip(times, values)
        return out

class VisualizerShow(LabradDjTemplateResource):
    path = "base_visualizer_show.html"

    def __init__(self, cxn=None):
        LabradDjTemplateResource.__init__(self, self.path, cxn)

    def render_GET(self, request):
        self._render(request)
        return NOT_DONE_YET

    @inlineCallbacks
    def _render(self, request):
        ses = getSessionExperiment(request)

        if all(ses):
            sequence_list = yield self._get_sequence_list(*ses)
            sequence = yield self._get_sequence(sequence_list, ses[1])
            (digital, analog) = self._get_channels(sequence)
            self.template_context['session'] = list(ses)
            self.template_context['digital'] = digital
            self.template_context['analog'] = analog
        else:
            self.template_context['session'] = ['','',0]

        request.write(bytes(self.template.render(self.template_context)))
        if not request.finished:
            request.finish()

    def _get_channels(self, sequence):
        channels = {} 
        for x in sequence['sequence'].keys():
            sp = x.split('@')
            channels[sp[-1]] = sp[0]
        
        locs = {}
        for x in sorted(channels.keys()):
            if x[0] in locs:
                locs[x[0]].append({'loc': x, 'name': channels[x]})
            else:
                locs[x[0]] = [{'loc': x, 'name': channels[x]}]
        for k in locs.keys():
            locs[k] = sorted(locs[k], key=lambda x: x['loc'])
        ls = [{"device": k, "channels": locs[k]} for k in sorted(locs.keys())]

        d = []
        a = []
        for l in ls:
            if l["device"] in DIGITAL_CHANNELS:
                d.append(l)
            else:
                a.append(l)
        return (d, a)

    @inlineCallbacks
    def _get_sequence_list(self, experiment, date, version):
        if experiment and date and version:
            experiment_vault = yield self.cxn.servers['experimentvault']
            data = yield experiment_vault.get_experiment_data(experiment, date, version)
            data = json.loads(data)
            returnValue(data['experiment']['sequencer']['sequence'][0])

    @inlineCallbacks
    def _get_sequence(self, sequences, date):
        sequence_vault = yield self.cxn.servers['sequencevault']
        sequence = yield sequence_vault.get_joined_sequence(sequences, date)
        returnValue(json.loads(sequence))


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
