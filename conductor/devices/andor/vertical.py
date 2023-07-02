import helpers

class Vertical(helpers.AndorDevice):
    """
    Vertical(helpers.AndorDevice)
    Andor camera for vertical imaging.
    .. code-block:: json
        # TODO: add example config
    """
    def __init__(self, config={}):
        super(Vertical, self).__init__('imaging_andor', 'vertical', config)