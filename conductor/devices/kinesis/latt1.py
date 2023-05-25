import helpers

class Latt1(helpers.STIRAPDevice):
    """
    Latt1(helpers.KinesisDevice)

    DDR25 rotation stage for Latt1 half waveplate

    .. code-block:: json

        {
            "kinesis": {
                "Latt1": [157, 330]
            }
        }
    """
    def __init__(self, config={}):
        super(Latt1, self).__init__('polarkrb_kinesis', 'latt1_waveplate', config)
