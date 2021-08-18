import helpers

class Update(helpers.AD9910Device):
    """
    Update(helpers.AD9910Device)

    AD9910 DDS for \|00\> to \|10\> and K RF (ARP and K cleaning pulse).
    """
    def __init__(self, config={}):
        super(Update, self).__init__(config)
