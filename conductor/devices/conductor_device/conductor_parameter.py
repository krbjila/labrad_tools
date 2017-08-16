from twisted.internet.defer import inlineCallbacks

class ConductorParameter(object):
    """ Base class/template for conductor parameters

    ConductorParameters are meant to provide a nice way to iterate/monitor
         settings/measurements each experimental cycle.

    The methods and properties defined here are all used by the conductor.
    It is therefore recommended that all conductor parameters inherit this class.

    the conductor calls parameters' update with higher priority first. 
    if priority <= 0, update does not get called.

    value_type is used to select preconfigured behaviors of 
        ConductorParameter.{value, advance, remaining_points, ...}
        
        value_type = 'single':
            default. 
            if _value is list, pops then returns first value in list
            else returns _value.
        
        value_type = 'list':
            a single value is a list
            if _value is list of lists, pops then returns first item
            else returns _value.

        value_type = 'once':
            _value is anything. 
            returns _value then sets _value to None

        value_type = 'data':
            _value is anything
            remaining_points = None
            returns _value

    """
    priority = 1
    value_type = 'single'

    def __init__(self, config):
        """ handle config (dict)
        
        upon creating a class instance, the conductor passes a config (dict).
        default behavior is to set (key, value) -> (instance attribute, value)
        """
        self._value = None
        for key, value in config.items():
            setattr(self, key, value)

    @inlineCallbacks
    def initialize(self):
        """ called only once, upon loading parameter into conductor

        use to initialize labrad connection and configure device.
        """
        yield None
    
    @inlineCallbacks
    def update(self):
        """ called at begining of every experimental cycle.
        
        use to send value to hardware.
        """
        yield None

    @inlineCallbacks
    def stop(self):
        """ close connections if you must """
        yield None

    @property
    def value(self):
        """ return value for current experimental run

        should return "something" representing parameter's current "value" (usually just a float)
        each experimental cycle, conductor saves output of value to data 

        _value possibly contains list of values to be iterated over.
        value_type should dictate how _value is processed to get current value.
        """
        if self.value_type == 'single':
            if type(self._value).__name__ == 'list':
                return self._value[0]
            else:
                return self._value
        elif self.value_type == 'list':
            if self._value:
                if type(self._value[0]).__name__ == 'list':
                    return self._value[0]
                else:
                    return self._value
        elif self.value_type == 'once':
            return self._value
        elif self.value_type == 'data':
            return self._value
        else:
            return None

    @value.setter
    def value(self, value):
        self._value = value
    
    def advance(self):
        """ change _value for next experimental run.

        if _value is list of values to be iterated over, remove previous value.
        value_type should dictate if/how elements are removed from _value.
        """
        if self.value_type == 'single':
            if type(self._value).__name__ == 'list':
                old = self._value.pop(0)
                if not len(self._value):
                    self.value = old
        elif self.value_type == 'list':
            if self._value:
                if type(self._value[0]).__name__ == 'list':
                    old = self._value.pop(0)
                    if not len(self._value):
                        self.value = old
        elif self.value_type == 'once':
            self._value = None

    def remaining_values(self):
        """ return how many values in _value queue.

        this should depend on value_type.
        """
        if self.priority:
            if self.value_type == 'single':
                if type(self._value).__name__ == 'list':
                    return len(self._value) - 1
            if self.value_type == 'list':
                if self._value:
                    if type(self._value[0]).__name__ == 'list':
                        return len(self._value) - 1

