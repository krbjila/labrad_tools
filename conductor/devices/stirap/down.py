import helpers

class Down(helpers.STIRAPDevice):
    """
    Down(helpers.STIRAPDevice)

    AD9910 DDS for stirap up leg

    .. code-block:: json

        {
            "stirap": {
                "down": [157,330]
            }
        }
    """
    def __init__(self, config={}):
        super(Down, self).__init__('down', config)
