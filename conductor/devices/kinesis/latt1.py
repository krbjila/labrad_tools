import helpers

class Latt1(helpers.KinesisDevice):
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
        super(Latt1, self).__init__('imaging_kinesis', 'latt1_waveplate', config)
