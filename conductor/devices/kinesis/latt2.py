import helpers

class Latt2(helpers.KinesisDevice):
    """
    Latt1(helpers.KinesisDevice)

    DDR25 rotation stage for Latt2 half waveplate

    .. code-block:: json

        {
            "kinesis": {
                "Latt2": [157, 330]
            }
        }
    """
    def __init__(self, config={}):
        super(Latt2, self).__init__('imaging_kinesis', 'latt2_waveplate', config)
