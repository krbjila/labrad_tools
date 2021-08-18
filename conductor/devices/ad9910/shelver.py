import helpers

class Shelver(helpers.AD9910Device):
    """
    Shelver(helpers.AD9910Device)

    AD9910 DDS for \|10\> to \|20\> RF.
    """
    def __init__(self, config={}):
        super(Shelver, self).__init__(config)