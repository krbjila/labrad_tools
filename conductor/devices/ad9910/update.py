import helpers

class Update(helpers.AD9910Device):
    """
    Update(helpers.AD9910Device)

    AD9910 DDS for K RF (ARP and K cleaning pulse). Example config:

    .. code-block:: json

        {
            "ad9910": {
            "update": {
                "program": [
                    {"mode": "sweep", "start": 246.0, "stop": 249, "dt": 1, "nsteps": 10000},
                    {"mode": "single", "freq": 200, "ampl": 0, "phase": 0},
                ]
            }
        }
    """
    def __init__(self, config={}):
        super(Update, self).__init__(config)
