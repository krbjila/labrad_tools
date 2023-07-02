import helpers

class Side(helpers.AndorDevice):
    """
    Side(helpers.AndorDevice)
    Andor camera for side and axial imaging.
    .. code-block:: json
        # TODO: add example config
    """
    def __init__(self, config={}):
        super(Side, self).__init__('imaging_andor', 'side', config)