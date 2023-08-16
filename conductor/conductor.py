"""
Coordinate setting and saving experiment parameters.

Experiment parameters are pretty much anything that could be changed from shot-to-shot of the experiment. Examples:

    - molecule RF frequency
    - function generator amplitude
    - the sequence of modules (``'highFieldRampRecompress'``, etc.)
    - analog/digital sequence variables, etc.

The primary abstraction over experiment parameters is the :mod:`conductor.devices.conductor_device.conductor_parameter.ConductorParameter`, which forms the base class for all custom parameters.

``ConductorParameter`` 's are organized by the physical or abstracted ``device`` they are associated with. For example, the :class:`kd1` device controls the RF synthesizer that drives the K D1 EOM. It has two parameters, :class:`Frequency` and :class:`Amplitude`.

:class:`ConductorParameter` provides two key methods:

    - :meth:`ConductorParameter.update`: Called to update the hardware with the current value of the parameter.
    - :meth:`ConductorParameter.advance`: Supports iteration over an iterable parameter value. For example, a list of dictionaries that define the DDS configuration over several shots.

New parameters can be added to the Conductor by subclassing :class:`ConductorParameter` and overriding the :meth:`ConductorParameter.update` method.

Parameters can be registered on-the-fly, but we typically enable them by including them in the ``config.json`` file. Here's an example:::

    {
        # ... setting conductor directories, etc.

        # Here is where we define Conductor's default parameters.
        "default_parameters": {
            # ... other parameters

            # The kd1 EOM RF synthesizer
            "kd1": {
                # Tell conductor to use the Frequency parameter
                "frequency": {
                    # This value will be loaded as a class variable (self.default)
                    "default": 1286
                },

                # Tell conductor to use the Amplitude parameter
                "amplitude": {
                    # This value will be loaded as a class variable (self.default)
                    "default": -11
                }
            },
        }
    }

(Note: the snippet above is commented for clarity, but we can't actually put comments in json :/)

..
    ### BEGIN NODE INFO
    [info]
    name = conductor
    version = 1.0
    description = 
    instancename = conductor

    [startup]
    cmdline = %PYTHON% %FILE%
    timeout = 20

    [shutdown]
    message = 987654321
    timeout = 20
    ### END NODE INFO
"""

import json
import os, errno, sys
sys.path.append(os.path.dirname(os.path.realpath(__file__)))

from collections import deque
from copy import deepcopy
from time import time, strftime
from datetime import datetime

from labrad.server import LabradServer
from labrad.server import setting
from labrad.server import Signal
from labrad.wrappers import connectAsync
from twisted.internet.reactor import callLater
from twisted.internet.defer import inlineCallbacks
from twisted.internet.defer import returnValue
from twisted.internet.threads import deferToThread

from lib.helpers import import_parameter
from lib.helpers import remaining_points
from lib.exceptions import ParameterAlreadyRegistered
from lib.exceptions import ParameterNotImported
from lib.exceptions import ParameterNotRegistered
from lib.exceptions import ParameterNotInitialized

from clients import variables_config

FILEBASE = '/dataserver/data/%Y/%m/%Y%m%d/shots'

class ConductorServer(LabradServer):
    """
    ConductorServer(LabradServer)
    
    Coordinate setting and saving experiment parameters.
    
    Parameters are classes defined in `./devices/ <https://github.com/krbjila/labrad_tools/tree/master/conductor/devices>`_.

        * parameters hold values representing real world attributes.
        * typically send/receive data to/from hardware.
        * see `./devices/conductor_device/conductor_parameter.py <https://github.com/krbjila/labrad_tools/blob/master/conductor/devices/conductor_device/conductor_parameter.py>`_ for documentation.
    
    Experiments specify parameter values to be iterated over and a filename for saving data.
    """

    name = 'conductor'
    parameters_updated = Signal(698124, 'signal: parameters_updated', 'b')
    """
        signal__parameters_updated
        
        Emitted when parameters are updated in ``self.set_parameters`` and ``self.advance_parameters``.

        .. note::
            Payload (bool): always ``True``.

        .. seealso::
            For help with Signals, see :ref:`labrad-tips-tricks-label`.
    """
    parameters_changed = Signal(698125, 'signal: parameters_changed', 's')
    """
        signal__parameters_changed
        
        Emitted when parameters are updated in ``self.set_parameters`` and ``self.advance_parameters``.

        This is very similar to ``signal__parameters_updated``, but its payload has the actual parameters changed and their new values.

        .. note::
            Payload (str): ``json.dumps`` string containing changed parameter values. Same format as returned by ``self.get_parameter_values()``

        .. seealso::
            For help with Signals, see :ref:`labrad-tips-tricks-label`.
    """
    experiment_started = Signal(696970, 'signal: experiment started', 'b')
    """
        signal__experiment_started
        
        Emitted in ``self.advance_experiment`` when a new experiment is started.

        .. note::
            Payload (bool): always ``True``.

        .. seealso::
            For help with Signals, see :ref:`labrad-tips-tricks-label`.
    """
    experiment_stopped = Signal(696971, 'signal: experiment stopped', 'b')
    """
        signal__experiment_stopped
        
        Emitted in ``self.advance_experiment`` when an experiment is stopped.

        .. note::
            Payload (bool): always ``True``.

        .. seealso::
            For help with Signals, see :ref:`labrad-tips-tricks-label`.
    """
    parameter_removed = Signal(696972, 'signal: parameter removed', 's')
    """
        signal__parameter_removed
        
        Emitted in ``self.remove_parameters`` when a parameter is removed.
        
        .. note::
            Payload (str): ``device_name + " " + parameter_name``.

        .. seealso::
            For help with Signals, see :ref:`labrad-tips-tricks-label`.
    """
    parameters_refreshed = Signal(696973, 'signal: parameters refreshed', 'b')
    """
        signal__parameters_refreshed
        
        Emitted in ``self.refresh_default_parameters``.

        .. note::
            Payload (bool): always ``True``.

        .. seealso::
            For help with Signals, see :ref:`labrad-tips-tricks-label`.
    """


    def __init__(self, config_path='./config.json'):
        self.parameters = {}
        self.experiment_queue = deque([])
        self.data = {}
        self.data_path = None
        self.do_print_delay = False
        self.shot = -1
        self.last_time = datetime.now()
        self.logging = False

        self.load_config(config_path)
        LabradServer.__init__(self)
        
        # added KM 09/10/2017
        self.advance_dict = {}
        self.advance_counter = 0
    
    def load_config(self, path=None):
        """
        load_config(self, path=None)

        Set instance attributes defined in json config.

        Args:
            path (str, optional): Location of the JSON config. Defaults to None, in which case the object's ``self.config_path`` is loaded.
        """        
        if path is not None:
            self.config_path = path
        with open(self.config_path, 'r') as infile:
            config = json.load(infile)
            for key, value in config.items():
                setattr(self, key, value)
        # TODO: RUN conductor/clients/variables_config.py and setattr from those also. Refer to conductor/clients/forceWriteValue in parameter_values_control.py

    def load_variables(self):
        """
        load_variables(self)

        Loads sequencer variables from ``clients/variables_config.py``.
        """
        self.variables = {}
        for v in variables_config.variables_dict:
            self.variables[v[0]] = float(v[1])
        update = json.dumps({"sequencer": self.variables})
        self.set_parameter_values(None, update)

    def initServer(self):
        """
        initServer(self)

        Registers default parameters and loads sequencer variables after connected to LabRAD
        """
        callLater(0.1, self.register_parameters, None, json.dumps(self.default_parameters))
        callLater(0.5, self.load_variables)


    # Re-initialize parameters
    # Added KM 03/18/18
    @setting(18)
    def refresh_default_parameters(self, c):
        """
        refresh_default_parameters(self, c)

        Tries to register all default parameters defined in the ``config.json`` file.
        
        Also checks that all sequencer variables are defined.

        Args:
            c: LabRAD context
        """

        # Signal to clients that parameters are being refreshed
        self.parameters_refreshed(True)

        # Loop through the devices defined in config.json
        for device in self.default_parameters:
            # If the device is not there, try to import its parameters
            if not device in self.parameters:
                params = {device: self.default_parameters[device]}
                try:
                    yield self.register_parameters(c, json.dumps(params))
                except ParameterNotImported:
                    print("{} not imported successfully".format(device))

            # If the device is loaded, check that all the parameters are there
            else:
                for param in self.default_parameters[device]:
                    # If a parameter is missing, try to import it
                    if not param in self.parameters[device]:
                        param_dict = {param: self.default_parameters[device][param]}
                        yield self.register_parameters(c, json.dumps({device: param_dict}))

        for k, v in self.variables.items():
            if not k in self.parameters["sequencer"]:
                self.set_parameter_values(c, json.dumps({"sequencer": {k: float(v)}}))


    @setting(2, parameters='s', generic_parameter='b', value_type='s', returns='b')
    def register_parameters(self, c, parameters, generic_parameter=False, value_type=None):
        """
        register_parameters(self, c, parameters, generic_parameter=False, value_type=None)

        Load parameters into conductor.
        
        Parameters are defined in conductor/devices/device_name/parameter_name.py.

        View defined parameters with conductor.available_parameters

        Args:
            c: LabRAD context
            parameters (str): ``json.dumps(...)`` of::

               {
                   device_name: {
                       parameter_name: {
                           parameter_config
                       }
               }

              where ``device_name`` is a string (e.g. "dds1"), ``parameter_name`` is a string (e.g. "frequency"), and ``parameter_config`` is passed to parameter's ``__init__``.

            generic_parameter (bool, optional): If ``True`` and no defined parameter is found, will create generic_parameter for holding values. Defaults to False.
            value_type (str, optional): e.g. "single", "list", "data". Defaults to None.

        Yields:
            bool: True if an error occurs
        """        
        for device_name, device_parameters in json.loads(parameters).items():
            for parameter_name, parameter_config in device_parameters.items():
                yield self.register_parameter(device_name, parameter_name, 
                        parameter_config, generic_parameter, value_type)

        returnValue(True)
    
    @inlineCallbacks
    def register_parameter(self, device_name, parameter_name, parameter_config,
                           generic_parameter, value_type):
        """register_parameter(self, device_name, parameter_name, parameter_config, generic_parameter, value_type)

        Populate ``self.parameters`` with specified parameter.

        Look in ``./devices/`` for specified parameter.

        If no suitable parameter is found and generic_parameter is ``True``, create generic parameter for holding values.

        Args:
            device_name (str): Name of device (e.g. "dds1")
            parameter_name (str): Name of parameter (e.g. "frequency")
            parameter_config (str): passed to parameter's ``__init__``
            generic_parameter (bool): Specifies whether or not to use ``devices/conductor_device/conductor_parameter.py`` if ``devices/device_name/parameter_name.py`` is not found.
            value_type (str): Description of parameter value (e.g. "single", "list", "data")

        Raises:
            ParameterAlreadyRegistered: if specified parameter is already in ``self.parameters``
            ParameterNotImported: if import of specified parameter fails
        """        
      
        if not self.parameters.get(device_name):
            self.parameters[device_name] = {}

        if self.parameters[device_name].get(parameter_name):
            raise ParameterAlreadyRegistered(device_name, parameter_name)
        else:
            Parameter = import_parameter(device_name, parameter_name, 
                                         generic_parameter)
            if not Parameter:
                raise ParameterNotImported(device_name, parameter_name)
            else:
                parameter = Parameter(parameter_config)
                parameter.device_name = device_name
                parameter.name = parameter_name
                if value_type is not None:
                    parameter.value_type = value_type
                self.parameters[device_name][parameter_name] = parameter
                
                print("{}'s {} registered".format(device_name, parameter_name))           
                yield parameter.initialize()
                yield self.update_parameter(parameter)

    @setting(3, parameters='s', returns='b')
    def remove_parameters(self, c, parameters):
        """
        remove_parameters(self, c, parameters)

        Remove specified parameters.

        Args:
            c: LabRAD context
            parameters (str): json dumped string (:py:meth:`json.dumps(...)`) of dict::

                {
                    device_name: {
                        parameter_name: None
                    }
                }

        Yields:
            bool: True
        """        
        for device_name, device_parameters in json.loads(parameters).items():
            for parameter_name, _ in device_parameters.items():
                yield self.remove_parameter(device_name, parameter_name)
        returnValue(True)
    
    @inlineCallbacks
    def remove_parameter(self, device_name, parameter_name):
        """
        remove_parameter(self, device_name, parameter_name)
        
        Remove specified parameter from ``self.parameters``.

        Args:
            device_name (str): Name of device (e.g. "dds1")
            parameter_name (str): Name of parameter (e.g. "frequency")
        Raises:
            ParameterNotRegistered: if specified parameter not in ``self.parameters``
        """
        try:
            parameter = self.parameters[device_name][parameter_name]
        except:
            raise ParameterNotRegistered(device_name, parameter_name)
        del self.parameters[device_name][parameter_name]
        if not self.parameters[device_name]:
            del self.parameters[device_name]
        yield parameter.stop()
        # Signal parameter removed
        self.parameter_removed(str(device_name + " " + parameter_name))

    @setting(4, parameters='s', generic_parameter='b', returns='b')
    def set_parameter_values(self, c, parameters, generic_parameter=False, 
                             value_type=None):
        """
        set_parameter_values(self, c, parameters, generic_parameter=False, value_type=None)

        Args:
            c: A LabRAD context
            parameters (str): json dumped string (:py:meth:`json.dumps(...)`) of dict::

                {
                    device_name: {
                        parameter_name: value
                    }
                }
            generic_parameter (bool, optional): Specifies whether or not to use ``devices/conductor_device/conductor_parameter.py`` if ``devices/device_name/parameter_name.py`` is not found. Defaults to False.
            value_type (str, optional): Description of parameter value (e.g. "single", "list", "data"). Defaults to None.

        Yields:
            bool: True
        """                             
        changed_parameters = {}
        changed = False

        for device_name, device_parameters in json.loads(parameters).items():
            for parameter_name, parameter_value in device_parameters.items():
                try:
                    changed = self.parameters[device_name][parameter_name] != parameter_value
                except KeyError:
                    changed = True
                
                yield self.set_parameter_value(device_name, parameter_name, 
                                               parameter_value, 
                                               generic_parameter, value_type)
                
                if changed:
                    # Do this to get the current value of parameter, not a list if there is a scan
                    pv = yield self.get_parameter_value(device_name, parameter_name)
                    try:
                        changed_parameters[device_name].update({parameter_name: pv})
                    except KeyError:
                        changed_parameters[device_name] = {parameter_name: pv}

        if len(changed_parameters): # Don't fire if no parameters were actually set
            yield self.parameters_updated(True)
            yield self.parameters_changed(json.dumps(changed_parameters))
        returnValue(True)

    @inlineCallbacks
    def set_parameter_value(self, device_name, parameter_name, parameter_value, generic_parameter=False, value_type=None):
        """
        set_parameter_value(self, device_name, parameter_name, parameter_value, generic_parameter=False, value_type=None)

        Args:
            device_name (str): Name of device (e.g. "dds1")
            parameter_name (str): Name of parameter (e.g. "frequency")
            parameter_value (any): Any type (e.g. 20E6)
            generic_parameter (bool, optional): Specifies whether or not to use ``devices/conductor_device/conductor_parameter.py`` if ``devices/device_name/parameter_name.py`` is not found. Defaults to False.
            value_type (str, optional): Description of parameter value (e.g. "single", "list", "data"). Defaults to None.
        Raises:
            ParameterNotImported: if import of specified parameter fails.

        """        
        try:
            self.parameters[device_name][parameter_name]
        except KeyError:
            if parameter_name[0] == '*':
                generic_parameter = True
            yield self.register_parameter(device_name, parameter_name, {}, 
                                          generic_parameter, value_type)
        self.parameters[device_name][parameter_name].value = parameter_value

    @setting(5, parameters='s', use_registry='b', returns='s')
    def get_parameter_values(self, c, parameters=None, use_registry=False):
        """
        get_parameter_values(self, c, parameters=None, use_registry=False)

        Gets specified parameter values.

        Args:
            c: LabRAD context
            parameters (str, optional): json dumped string (:py:meth:`json.dumps(...)`) of dict::

                {
                    device_name: {
                        parameter_name: None
                    }
                }
            
              Defaults to None, in which case all parameter values are returned.
            use_registry (bool, optional): Look for parameter in registry (deprecated). Defaults to False.

        Yields:
            str: json dumped string (:py:meth:`json.dumps(...)`) of dict of parameter values
        """        
        if parameters is None:
            parameters = {dn: dp.keys() for dn, dp in self.parameters.items()}
        else:
            parameters = json.loads(parameters)

        parameter_values = {}
        for device_name, device_parameters in parameters.items():
            parameter_values[device_name] = {}
            for parameter_name in device_parameters:
                parameter_values[device_name][parameter_name] = \
                        yield self.get_parameter_value(device_name, 
                                                       parameter_name,
                                                       use_registry)
        returnValue(json.dumps(parameter_values))

    @inlineCallbacks
    def get_parameter_value(self, device_name, parameter_name, use_registry=False):
        """
        get_parameter_value(self, device_name, parameter_name, use_registry=False)

        Args:
            device_name (str): Name of device (e.g. "dds1")
            parameter_name (str): Name of parameter (e.g. "frequency")
            use_registry (bool, optional): Look for parameter in registry (deprecated). Defaults to False.

        Raises:
            Exception: Throws an error if an invalid parameter is used.

        Yields:
            any: The value of the selected parameter
        """        
        message = None
        try:
            try: 
                parameter = self.parameters[device_name][parameter_name]
                value = parameter.value
            except:
                parameters_filename = self.parameters_directory + 'current_parameters.json'
                with open(parameters_filename, 'r') as infile:
                    old_parameters = json.load(infile)
                    value = old_parameters[device_name][parameter_name]
                    yield self.set_parameter_value(device_name, parameter_name, value, True)
        except:
            if use_registry:
                print('looking in registry for parameter {}'.format(device_name + parameter_name))
                print('this feature will be depreciated')
                try: 
                    yield self.client.registry.cd(self.registry_directory
                                                  + [device_name])
                    value = yield self.client.registry.get(parameter_name)
                    config = json.dumps({device_name: {parameter_name: value}})
                    yield self.set_parameter_values(None, config, True)
                except Exception as e:
                    print(e)
                    message = 'unable to get most recent value for\
                               {} {}'.format(device_name, parameter_name)
            else:
                message = '{} {} is not an active parameter'.format(device_name,
                                                                 parameter_name)
        if message:
            raise Exception(message)
        returnValue(value)
    
    @setting(8, experiment='s', run_next='b', returns='i')
    def queue_experiment(self, c, experiment, run_next=False):
        """
        queue_experiment(self, c, experiment, run_next=False)

        Args:
            c: LabRAD context
            experiment (str): json-dumped string with keys 

                * ``name``' (str): Some string. Required.
                * ``parameter_values`` (Dict, optional): {name: value}.
                * ``append data`` (bool, optional): Save data to previous file?
                * ``loop`` (bool, optional): Inserts experiment back into begining of queue.
            run_next (bool, optional): Add the experiment at the beginning of the queue. Defaults to False.

        Returns:
            int: Number of experiments in the queue
        """        
        if run_next:
            self.experiment_queue.appendleft(json.loads(experiment))
        else:
            self.experiment_queue.append(json.loads(experiment))
        return len(self.experiment_queue)

    @setting(9, experiment_queue='s', returns='i')
    def set_experiment_queue(self, c, experiment_queue=None):
        """
        set_experiment_queue(self, c, experiment_queue=None)

        Loads the experiments in ``experiment_queue`` into the queue.

        Args:
            c: LabRAD context
            experiment_queue (str, optional): json-dumped list of experiments. See :meth:`queue_experiment` for format of an experiment. Defaults to None.

        Returns:
            int: Number of experiments in the queue
        """
        self.experiment_queue = deque([])
        if experiment_queue:
            experiment_queue = json.loads(experiment_queue)
            for experiment in experiment_queue:
                self.experiment_queue.append(experiment)
        return len(self.experiment_queue)

    @setting(10, returns='b')
    def stop_experiment(self, c):
        """
        stop_experiment(self, c)

        Sets ``self.parameters`` to run the default sequence and sends the ``experiment_stopped`` signal.

        Do not call this directly. Used internally in :meth:`abort_experiment`, which you should call.

        Args:
            c: LabRAD context

        Returns:
            bool: True
        """
        # replace parameter value lists with single value.
        for device_name, device_parameters in self.parameters.items():
            for parameter_name, parameter in device_parameters.items():
                parameter.value = parameter.value
                if parameter_name == 'sequence':
                    parameter.value = [parameter.default_sequence]
                # Ensure that Rb uwave synth outputs default
                if parameter_name == 'enable' and device_name == 'E8257D':
                    parameter.value = 0
                # Ensure that the STIRAP DDS's are not rewritten
                if device_name == 'stirap' and (parameter_name == 'up' or parameter_name == 'down'):
                    parameter.value = []
        self.data = {}
        self.data_path = None
        self.experiment_stopped(True)
        return True

    # KM added 09/10/2017
    # 
    @setting(17)
    def abort_experiment(self, c):
        """
        abort_experiment(self, c)

        Abort the experiment immediately, then run defaults. Also cancels queued experiments.

        Args:
            c: LabRAD context
        """        
        yield self._advance_logging(True)
        for ID, call in self.advance_dict.items():
            try:
                call.cancel()
            except:
                pass
        self.advance_dict = {}
        self.stop_experiment(c)
        for device_name, device_parameters in self.parameters.items():
            for parameter_name, parameter in device_parameters.items():
                self.update_parameter(parameter)
 
    @setting(13, returns='s')
    def get_data(self, c):
        """
        get_data(self, c)

        Returns json-dumped dictionary of current parameter values.

        Args:
            c: LabRAD context

        Returns:
            str: json-dumped dictionary of current parameter values
        """
        return json.dumps(self.data)
    
    @inlineCallbacks
    def advance_experiment(self):
        """
        advance_experiment(self)

        Runs the next queued experiment. Advances logging.
        """
        if len(self.experiment_queue):
            # send signal that experiment has stopped
            self.experiment_stopped(True)
            # get next experiment from queue and keep a copy
            experiment = self.experiment_queue.popleft()
            experiment_copy = deepcopy(experiment)

            if "name" in experiment and "default" not in experiment["name"]:
                #TODO: Move save_parameters here
                yield self._advance_logging(False)
            else:
                yield self._advance_logging(True)
            
            parameter_values = experiment.get('parameter_values')
            if parameter_values:
                yield self.set_parameter_values(None, json.dumps(parameter_values))
            # signal that experiment has started again
            self.experiment_started(True)
            # if this experiment should loop, append to begining of queue
            if experiment.get('loop'):
                # now we require appending data
                experiment_copy['append_data'] = True
                # add experiment to begining of queue
                self.experiment_queue.appendleft(experiment_copy)
            
            if not experiment.get('append_data'):
                self.data = {}

                # determine data path
                timestr = strftime('%Y%m%d')
                data_directory = self.data_directory.format(timestr)
                self.experiment_name = experiment['name']
                data_path = lambda i: str(data_directory 
                                          + experiment['name'] 
                                          + '#{}'.format(i))
                iteration = 0 
                while os.path.isfile(data_path(iteration)):
                    iteration += 1
                self.data_path = data_path(iteration)
                
                if not os.path.exists(data_directory):
                    os.mkdir(data_directory)

            returnValue(True)
        else:
            self.data = {}
            if self.data_path:
                print('experiment queue is empty')
            # signal that experiment has stopped
            self.experiment_stopped(True)
            self.data_path = None
            returnValue(False)

    @inlineCallbacks
    def advance_parameters(self):
        """
        advance_parameters(self)
        
        Get new parameter values then send to devices. Calls :meth:`advance_experiment`.
        """
        advanced = False
        # check if we need to load next experiment
        pts = remaining_points(self.parameters)
        if not pts:
            advanced = yield self.advance_experiment()
        else:
            print('remaining points: {}'.format(pts)) 
            #TODO: Add save_parameters here
            if self.logging:
                yield self._advance_logging(True)
                yield self._advance_logging(False)

        # sort by priority. higher priority is called first. 
        priority_parameters = [parameter for device_name, device_parameters
                                         in self.parameters.items()
                                         for parameter_name, parameter 
                                         in device_parameters.items()
                                         if parameter.priority]

        # advance parameter values if parameter has priority
        if not advanced:
            changed_parameters = {}
            changed = False

            for parameter in priority_parameters:
                old_pv = yield self.get_parameter_value(parameter.device_name, parameter.name)
                parameter.advance()
                new_pv = yield self.get_parameter_value(parameter.device_name, parameter.name)
                
                if old_pv != new_pv:
                    try:
                        changed_parameters[parameter.device_name].update({parameter.name: new_pv})
                    except KeyError:
                        changed_parameters[parameter.device_name] = {parameter.name: new_pv}
            
            if len(changed_parameters):
                self.parameters_changed(json.dumps(changed_parameters))
        
        # call parameter updates in order of priority. 
        # 1 is called last. 0 is never called.
        for parameter in sorted(priority_parameters, key=lambda x: x.priority)[::-1]:
            # if parameter.device_name != 'sequencer' or "*" not in parameter.name:
            #     print('priority: {}: updating {}\'s {}'.format(parameter.priority, parameter.device_name, parameter.name))
            yield self.update_parameter(parameter)

        # signal update
        yield self.parameters_updated(True)

    @inlineCallbacks
    def update_parameter(self, parameter):
        """
        update_parameter(self, parameter)

        Have device update parameter value. Prints a warning message and removes the parameter if the parameter can't be updated.

        Args:
            parameter (ConductorParameter): The parameter to update.
        """        
        try:
            yield parameter.update()
        except Exception as e:
            # remove parameter is update failed.
            print(e)
            print('could not update {}\'s {}. removing parameter'.format(
                    parameter.device_name, parameter.name))
            yield self.remove_parameter(parameter.device_name, parameter.name)
    
    def save_parameters(self):
        """
        save_parameters(self)

        Save to disk a json-dumped dictionary of current parameter values ``self.data``. The file is saved in the folder on the dataserver determined by the logging server's current shot number.
        """
        # save data to disk
        if self.data:
            try:
                data_length = max([len(p) for dp in self.data.values()
                                        for p in dp.values()])
            except Exception as e:
                data_length = 0
                print("saving data failed due to error:", e)
        else:
            data_length = 0
        
        for device_name, device_parameters in self.parameters.items():
            if not self.data.get(device_name):
                self.data[device_name] = {}
            for parameter_name, parameter in device_parameters.items():
                if not self.data[device_name].get(parameter_name):
                    self.data[device_name][parameter_name] = []
                parameter_data = self.data[device_name][parameter_name] 
                while len(parameter_data) < data_length:
                    parameter_data.append(None)
                new_value = parameter.value
                parameter_data.append(new_value)
        
        if self.data_path:
            self.data['shot_number'] = {"shot": [self.shot]}

            if not 'defaults' in self.data_path:
                s = json.dumps(self.data, default=lambda x: None, sort_keys=True, indent=2)
                with open(self.data_path, 'w+') as outfile:
                    outfile.write(s)
                print('saving data to {}'.format(self.data_path))
                
                path =  "%s/%d/" % (self.last_time.strftime(FILEBASE), self.shot)
                try:
                    os.makedirs(path)
                except OSError as e:
                    if e.errno != errno.EEXIST:
                        print("Could not connect to data server: ", e)

                try:
                    with open(path + "sequence.json", 'w+') as outfile:
                        outfile.write(s)
                    print('saving data to {}'.format(path + "sequence.json"))
                except Exception as e:
                    print("Could not connect to data server: ", e)

    @inlineCallbacks
    def stopServer(self):
        """
        stopServer(self)

        Called when the server is stopped. Saves the current parameters before closing.
        """
        yield self._advance_logging(True)

        parameters_filename = self.parameters_directory + 'current_parameters.json'
        if os.path.isfile(parameters_filename):
            with open(parameters_filename, 'r') as infile:
                old_parameters = json.load(infile)
        else:
            old_parameters = {}
        parameters = deepcopy(old_parameters)
        for device_name, device_parameters in self.parameters.items():
            if not parameters.get(device_name):
                parameters[device_name] = {}
            for parameter_name, parameter in device_parameters.items():
                parameters[device_name][parameter_name] = parameter.value
        
        parameters_filename = self.parameters_directory + 'current_parameters.json'
        with open(parameters_filename, 'w') as outfile:
            json.dump(parameters, outfile)

        parameters_filename = self.parameters_directory + '{}.json'.format(
                                  strftime(self.time_format))
        with open(parameters_filename, 'w') as outfile:
            json.dump(parameters, outfile)

    # KM edited 09/10/2017
    @setting(15)
    def advance(self, c, delay=0, **kwargs):
        """
        advance(self, c, delay=0, **kwargs)

        Calls :meth:advance_parameters after a time of ``delay``. Keeps track of experiments that are queued in ``self.advance_dict`` so they can be cancelled.

        Args:
            c: LabRAD context
            delay (int, optional): The delay in seconds before advancing the experiment. Defaults to 0.
        """        
        if delay:
            self.advance_dict[str(self.advance_counter)] = callLater(delay, self.advance, c, ID=self.advance_counter)
            self.advance_counter=0
            while str(self.advance_counter) in self.advance_dict.keys():
                self.advance_counter += 1 
        else:
            ti = time()
            #TODO: Remove save_parameters here
            yield deferToThread(self.save_parameters)
            yield self.advance_parameters()
            tf = time()
            if 'ID' in kwargs:
                del self.advance_dict[str(kwargs['ID'])]
            if self.do_print_delay:
                print('delay: {}'.format(tf-ti))

    @setting(1700, end='b')
    def advance_logging(self, c, end = False):
        """
        advance_logging(self, c, end = False)

        Tells the logging server to begin logging for the next shot. Shot number is reset daily.

        Args:
            c: LabRAD context
            end (bool, optional): Stops logging the current shot if `True`. Defaults to False.
        """        
        yield self._advance_logging(end)

    @inlineCallbacks
    def _advance_logging(self, end = False):
        """
        _advance_logging(self, end = False)

        Tells the logging server to begin logging for the next shot. Shot number is reset daily.

        Do not use directly; called by :meth:`advance_logging`.

        Args:
            end (bool, optional): Stops logging the current shot if `True`. Defaults to False.
        """
        cur_time = datetime.now()

        try:
            logging = yield self.client.servers['imaging_logging']
            logging.set_name("conductor")
        except Exception as e:
            print("Could not connect to logging server: ", e)

        if not end:
            try:
                self.shot = yield logging.get_next_shot()
                yield logging.set_shot(self.shot)
                yield logging.log("Started shot %d" % (self.shot), cur_time)
                print("Started logging shot %d" % (self.shot))
                self.logging = True
            except Exception as e:
                print("Could not start logging shot: ", e)
        else:
            try:
                if self.logging:
                    yield logging.log("Finished shot %d" % (self.shot), cur_time)
                    yield logging.set_shot()
                    print("Stopped logging shot %d" % (self.shot))
                    self.logging = False
            except Exception as e:
                print("Could not stop logging shot: ", e)

    @setting(16, do_print_delay='b', returns='b')
    def print_delay(self, c, do_print_delay=None):
        """
        print_delay(self, c, do_print_delay=None)

        Args:
            c: LabRAD context
            do_print_delay (bool, optional): Sets whether the delay is printed by :meth:`advance`. Defaults to None.

        Returns:
            bool: do_print_delay
        """
        if do_print_delay is not None:
            self.do_print_delay = do_print_delay
        return self.do_print_delay

if __name__ == "__main__":
    from labrad import util
    server = ConductorServer()
    util.runServer(server)
