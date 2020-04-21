from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.web.server import Site, NOT_DONE_YET, Session
from twisted.web.resource import Resource, NoResource
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

from krbtools_resources import LabradDjTemplateResource

TEMPLATE_DIR = '../../app/templates/'

PRE_OPEN = "<pre style=\"word-wrap: break-word; white-space: pre-wrap\">"
PRE_CLOSE = "</pre>"

DIGITAL_CHANNELS = [chr(x) for x in range(ord("A"), ord("H") + 1)]

TIME_PRECISION = 9 # 1 ns precision; expt resolution is only 100 ns, but use this to avoid rounding errors

class KRbSequenceAPI(Resource):
    def __init__(self, cxn):
        Resource.__init__(self)
        self.cxn = cxn

        self.experiments = Experiments(cxn)
        self.sequences = Sequences(cxn)
        self.channels = Channels(cxn)
        self.parameters = Parameters(cxn)

        self.putChild("experiments", self.experiments)
        self.putChild("sequences", self.sequences)
        self.putChild("channels", self.channels)
        self.putChild("parameters", self.parameters)

        self.sequence_versions = ExperimentSequences(cxn)
        self.plottables = ExperimentPlottables(cxn)
        self.parameterized = ExperimentParameterized(cxn)

        self.experiments.putChild("sequences", self.sequence_versions)
        self.experiments.putChild("plottable", self.plottables)
        self.experiments.putChild("parameterized", self.parameterized)

class Parameters(Resource):
    def __init__(self, cxn):
        Resource.__init__(self)
        self.cxn = cxn
        self.template_context = {}

    def render_GET(self, request):
        self._render_get(request)
        return NOT_DONE_YET

    @inlineCallbacks
    def _render_get(self, request):
        conductor = yield self.cxn.servers['conductor']
        pvs = yield conductor.get_parameter_values()
        pvs = json.loads(pvs)
        out = json.dumps(pvs, sort_keys=True, indent=4, separators=(',', ': '))
        
        if not "application/json" in request.getHeader('accept'):
            out = PRE_OPEN + out + PRE_CLOSE
            
        request.write(bytes(out))

        if not request.finished:
            request.finish()


class ExperimentsBase(Resource):
    def __init__(self, cxn):
        Resource.__init__(self)
        self.cxn = cxn
        self.template_context = {}

    def render_GET(self, request):
        self._render_get(request)
        return NOT_DONE_YET

    @inlineCallbacks
    def _render_get(self, request):
        out = ""

        (expts, dates, versions) = yield self._get_experiments()

        if all(k in request.args.keys() for k in ['name', 'date', 'version']):
            expt = request.args['name'][0]
            date = request.args['date'][0]
            v = int(request.args['version'][0])

            if v in versions[expt][date]:
                out = yield self.resourceFound(expt, date, v)
            else:
                out = json.dumps({"message": "not found"}, sort_keys=True, indent=4, separators=(',', ': '))

        else:
            out = yield self.noQueryString()

        if not "application/json" in request.getHeader('accept'):
            out = PRE_OPEN + out + PRE_CLOSE
        request.write(bytes(out))

        if not request.finished:
            request.finish()

    def resourceFound(self, expt, date, version):
        pass

    @inlineCallbacks
    def noQueryString(self):
        (expts, dates, versions) = yield self._get_experiments()
        out = json.dumps(versions, sort_keys=True, indent=4, separators=(',', ': '))
        returnValue(out)

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

    @inlineCallbacks
    def _get_joined_sequence(self, sequences, date):
        sequence_vault = yield self.cxn.servers['sequencevault']
        joined = yield sequence_vault.get_joined_sequence(sequences, date)
        returnValue(json.loads(joined))


class Experiments(ExperimentsBase):
    @inlineCallbacks
    def resourceFound(self, expt, date, version):
        ret = yield self._get_experiment_parameters(expt, date, version)
        out = {"name": expt, "date": date, "version": version, "data": ret['experiment']}
        out = json.dumps(out, sort_keys=True, indent=4, separators=(',', ': '))
        returnValue(out)

class ExperimentSequences(ExperimentsBase):
    @inlineCallbacks
    def resourceFound(self, expt, date, version):
        ret = yield self._get_experiment_parameters(expt, date, version)
        sequences = ret['experiment']['sequencer']['sequence'][0]
        durations = yield self._get_sequence_durations(sequences, date)
        arr = [{'name': s, 'date': d, 'duration': dd[0], 'time_variables': dd[1]} for s, d, dd in zip(sequences, ret['dates'], durations)] 
        returnValue(json.dumps(arr, sort_keys=True, indent=4, separators=(',', ': ')))

class ExperimentPlottables(ExperimentsBase):
    @inlineCallbacks
    def _get_substituted_sequence(self, sequences, date):
        sequence_vault = yield self.cxn.servers['sequencevault']
        subbed = yield sequence_vault.get_substituted_sequence(sequences, date)
        returnValue(json.loads(subbed))

    @inlineCallbacks
    def resourceFound(self, expt, date, version):
        data = yield self._get_experiment_parameters(expt, date, version)
        sequence_list = data['experiment']['sequencer']['sequence'][0]

        sequence = yield self._get_joined_sequence(sequence_list, date)
        substituted_sequence = yield self._get_substituted_sequence(sequence_list, date)
        plottable = yield self.get_plottable(substituted_sequence)
        out = {'meta': sequence['meta'], 'plottable': plottable}
        returnValue(json.dumps(out, sort_keys=True, indent=4, separators=(',', ': ')))

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

class ExperimentParameterized(ExperimentsBase):
    @inlineCallbacks
    def resourceFound(self, expt, date, version):
        data = yield self._get_experiment_parameters(expt, date, version)
        sequence_list = data['experiment']['sequencer']['sequence'][0]

        sequence = yield self._get_joined_sequence(sequence_list, date)
        parameterized_sequence = yield self._get_joined_sequence(sequence_list, date)
        returnValue(json.dumps(parameterized_sequence, sort_keys=True, indent=4, separators=(',', ': ')))

class SequencesBase(Resource):
    def __init__(self, cxn):
        Resource.__init__(self)
        self.cxn = cxn
        self.template_context = {}

    def render_GET(self, request):
        self._render_get(request)
        return NOT_DONE_YET

    @inlineCallbacks
    def _render_get(self, request):
        out = ""

        available = yield self._get_sequence_versions()

        if all(k in request.args.keys() for k in ['name', 'date']):
            name = request.args['name'][0]
            date = request.args['date'][0]

            out = json.dumps({"message": "not found"}, sort_keys=True, indent=4, separators=(',', ': '))
            for x in available:
                print x
                if name == x['name'] and date in x['dates']:
                    out = yield self.resourceFound(name, date)
                    break
        else:
            out = yield self.noQueryString(available)

        if not "application/json" in request.getHeader('accept'):
            out = PRE_OPEN + out + PRE_CLOSE
        request.write(bytes(out))

        if not request.finished:
            request.finish()

    def resourceFound(self, name, date):
        pass

    def noQueryString(self, x):
        out = json.dumps(x, sort_keys=True, indent=4, separators=(',', ': '))
        return out

    @inlineCallbacks
    def _get_sequence_versions(self):
        sequence_vault = yield self.cxn.servers['sequencevault']
        available = yield sequence_vault.get_sequences()

        out = []
        for s in available:
            dates = yield sequence_vault.get_dates(s)
            out.append({"name": s, "dates": dates}) 
        returnValue(out)

    @inlineCallbacks
    def _get_joined_sequence(self, sequences, date):
        sequence_vault = yield self.cxn.servers['sequencevault']
        joined = yield sequence_vault.get_joined_sequence(sequences, date)
        returnValue(json.loads(joined))

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

class Sequences(SequencesBase):
    @inlineCallbacks
    def resourceFound(self, name, date):
        s = yield self._get_joined_sequence([name], date)
        ret = {"name": name, "date": date, "data": s}
        out = json.dumps(ret, sort_keys=True, indent=4, separators=(',', ': '))
        returnValue(out)

class Channels(Resource):
    def __init__(self, cxn):
        Resource.__init__(self)
        self.cxn = cxn
        self.template_context = {}

    def render_GET(self, request):
        self._render_get(request)
        return NOT_DONE_YET

    @inlineCallbacks
    def _render_get(self, request):
        out = ""

        all_channels = yield self._get_channels()

        if 'channel_type' in request.args.keys():
            channel_type = request.args['channel_type'][0]

            out = json.dumps({"message": "not found"}, sort_keys=True, indent=4, separators=(',', ': '))

            if 'sort' in request.args.keys() and request.args['sort'][0]:
                out = yield self.returnSorted(all_channels, channel_type, out)
            else:
                out = yield self.returnDict(all_channels, channel_type, out)
        else:
            out = yield self.noQueryString(all_channels)

        if not "application/json" in request.getHeader('accept'):
            out = PRE_OPEN + out + PRE_CLOSE
        request.write(bytes(out))

        if not request.finished:
            request.finish()

    def returnDict(self, all_channels, channel_type, default_out):
        out = {}
        for k,v in all_channels.items():
            if v['channel_type'] == channel_type:
                out[k] = v
        if len(out.keys()):
            return json.dumps(out, sort_keys=True, indent=4, separators=(',', ': '))
        else:
            return default_out

    def returnSorted(self, all_channels, channel_type, default_out):
        out = []
        for k,v in all_channels.items():
            if v['channel_type'] == channel_type:
                out.append({'k': v['loc'], 'v': v})
        if len(out):
            out = sorted(out, key=lambda x: x['k'])
            return json.dumps(out, sort_keys=True, indent=4, separators=(',', ': '))
        else:
            return default_out

    def noQueryString(self, channels):
        out = {}
        for k,v in channels.items():
            if v['channel_type'] not in out:
                out[v['channel_type']] = [{'k': v['loc'], 'v': v}]
            else:
                out[v['channel_type']].append({'k': v['loc'], 'v': v})
        for k in out.keys():
            out[k] = sorted(out[k], key=lambda x: x['k'])                
        return json.dumps(out, sort_keys=True, indent=4, separators=(',', ': '))

    @inlineCallbacks
    def _get_channels(self):
        sequencer = yield self.cxn.servers['sequencer']
        channels = yield sequencer.get_channels()
        returnValue(json.loads(channels))