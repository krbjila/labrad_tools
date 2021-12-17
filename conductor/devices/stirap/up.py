import helpers

class Up(helpers.STIRAPDevice):
    """
    Up(helpers.STIRAPDevice)

    AD9910 DDS for stirap up leg

    .. code-block:: json

        {
            "stirap": {
                "up": [80,140]
            }
        }
    """
    def __init__(self, config={}):
        super(Up, self).__init__('up', config)