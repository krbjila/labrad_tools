import helpers

class Shelver(helpers.AD9910Device):
    def __init__(self, config={}):
        super(Shelver, self).__init__(config)