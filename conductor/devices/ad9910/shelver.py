import helpers

class Shelver(helpers.AD9910Device):
    """
    Shelver(helpers.AD9910Device)

    AD9910 DDS for \|10\> to \|20\> RF. Example config:

    .. code-block:: json

        {
            "ad9910": {
                "shelver": {
                    "program": [
                        {"mode": "single", "freq": 249.837, "ampl": -18, "phase": 0},
                        {"mode": "single", "freq": 249.837, "ampl": -18, "phase": 0},
                    ],
                    "profiles": [{"profile": 0, "freq": 10, "ampl": 0, "phase": 0}]
                }
            }
        }
    """
    def __init__(self, config={}):
        super(Shelver, self).__init__(config)