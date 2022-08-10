from esida.koeppen_parameter import KoeppenParameter

class koeppen_a(KoeppenParameter):

    def __init__(self):
        super().__init__()

        # tropical
        self.area_of_interest = [
            1,
            2,
            3
        ]
