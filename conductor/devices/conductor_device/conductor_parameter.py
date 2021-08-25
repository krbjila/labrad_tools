from twisted.internet.defer import inlineCallbacks

class ConductorParameter(object):
    """
    ConductorParameter(object)
    
    Base class/template for conductor parameters

    ConductorParameters are meant to provide a nice way to iterate/monitor settings/measurements each experimental cycle.

    The methods and properties defined here are all used by the conductor. It is therefore recommended that all conductor parameters inherit this class.

    The conductor calls parameters' update with higher priority first. If ``priority <= 0``, update does not get called.

    ``value_type`` is used to select preconfigured behaviors of ``ConductorParameter.{value, advance, remaining_points, ...}``
        
        * value_type = 'single':
            Default. 

            If ``_value`` is list, pops then returns first value in list

            Else returns ``_value``.
        
        * value_type = 'list':
            A single value is a list.

            If ``_value`` is list of lists, pops then returns first item.

            Else returns ``_value``.

        * value_type = 'once':
            ``_value`` is anything.

            Returns ``_value`` then sets ``_value`` to ``None``.

        * value_type = 'data':
            ``_value`` is anything.

            remaining_points = `None`

            Returns ``_value``.

    """
    priority = 1
    value_type = 'single'
    critical = False

    def __init__(self, config):
        """
        __init__(self, config)

        Handle config (dict)
        
        Upon creating a class instance, the conductor passes a config (dict).

        Default behavior is to set (key, value) -\> (instance attribute, value)
        """
        self._value = None
        for key, value in config.items():
            setattr(self, key, value)

    @inlineCallbacks
    def initialize(self):
        """
        initialize(self)

        Called only once, upon loading parameter into conductor.

        Use to initialize LabRAD connection and configure device.
        """
        yield None
    
    @inlineCallbacks
    def update(self):
        """
        update(self)
        
        Called at begining of every experimental cycle.
        
        New conductor parameters should override this method to communicate with hardware.
        """
        yield None

    @inlineCallbacks
    def stop(self):
        """
        stop(self)
        
        Close connections if you must.
        """
        yield None

    @property
    def value(self):
        """
        value(self)
        
        Return value for current experimental run.

        Should return "something" representing parameter's current "value" (usually just a float)  each experimental cycle, conductor saves output of value to data.

        ``_value`` possibly contains list of values to be iterated over.

        ``value_type`` should dictate how ``value`` is processed to get current value.
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
        """
        advance(self)
        
        Change ``_value`` for next experimental run.

        If ``_value`` is list of values to be iterated over, remove previous value.
        
        Value_type should dictate if/how elements are removed from ``_value``.
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
        """
        remaining_values(self)
        
        Return how many values in ``_value`` queue.

        this should depend on ``value_type``.
        """
        if self.priority:
            if self.value_type == 'single':
                if type(self._value).__name__ == 'list':
                    return len(self._value) - 1
            if self.value_type == 'list':
                if self._value:
                    if type(self._value[0]).__name__ == 'list':
                        return len(self._value) - 1

