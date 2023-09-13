import helpers

class RbMOT(helpers.AD9910Device):
    def __init__(self, config={}):
        calibration = {
            1: 1/0.9060735228939916,
            2: 1/0.8211087379097065,
            3: 1/0.921183140809069,
            4: 1/0.873316437926352
        }
        super(RbMOT, self).__init__("RbMOT", "AIN0", "*RbMOT", calibration, config)
