import helpers

class Update(helpers.AD9910Device):
    """
    Update(helpers.AD9910Device)

    AD9910 DDS for \|00\> to \|10\> and K RF (ARP and K cleaning pulse). Example config:

    .. code-block:: json

        {
            "ad9910": {
            "update": {
                "program": [
                    {"mode": "sweep", "start": 246.0, "stop": 249, "dt": 1, "nsteps": 10000},
                    {"mode": "single", "freq": 200, "ampl": 0, "phase": 0},
                ],
                "profiles": [
                    {"profile": 3, "freq": 248, "ampl": -2, "phase": 0},
                    {"profile": 7, "freq": 248, "ampl": -2, "phase": 0},
                    {"profile": 5, "freq": 248, "ampl": -2, "phase": 0},
                    {"profile": 1, "freq": 248, "ampl": 0, "phase": 0},
                    {"profile": 4, "freq": 248, "ampl": -3, "phase": 0},
                    {"profile": 2, "freq": 248.8, "ampl": 0, "phase": 0}
                ]
            }
        }
    """
    def __init__(self, config={}):
        super(Update, self).__init__(config)
