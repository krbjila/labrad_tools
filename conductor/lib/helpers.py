import os
import sys
sys.path.append('devices')

from inflection import camelize

def import_parameter(device_name, parameter_name, generic=False):
    """ import specified parameter class 
    
    look in conductor/device_name/parameter_name.py for ParameterName.
    return if found.
    default to conductor/conductor_device/conductor_parameter.py optional.

    Args:
        device_name: string e.g. "dds1"
        parameter_name: string e.g. "frequency"
        generic: bool. whether or not to use ConductorParameter base class
            if conductor/device_name/parameter_name.py is not found.

    Returns:
        parameter class or None if appropriate parameter class cannot be found.
    """
    path = os.path.join('devices', device_name, parameter_name)
    if not os.path.isfile(path+'.py'):
        if generic:
            device_name = 'conductor_device'
            parameter_name = 'conductor_parameter'
        else: 
            return None
    module_name = 'devices.{}.{}'.format(device_name, parameter_name)
    class_name = camelize(parameter_name)
    module = __import__(module_name, fromlist=[class_name])
    reload(module)
    return getattr(module, class_name)

def remaining_points(parameters):
    """ number of experimental cycles remaining in experiment

    each parameter has remaining_values method representing number of values
    remaining in queue.

    Args:
        parameters: dict ({device_name: {parameter_name: parameter}})

    Returns:
        int
    """
    return max([parameter.remaining_values() 
        for device_parameters in parameters.values()
        for parameter in device_parameters.values()])
