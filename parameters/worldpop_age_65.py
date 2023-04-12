from esida.sexage_parameter import SexageParameter

class worldpop_age_65(SexageParameter):

    def __init__(self):
        super().__init__()
        self.ages = [65, 70, 75, 80]
