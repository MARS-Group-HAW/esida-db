from esida.koeppen_parameter import KoeppenParameter

class koeppen_e(KoeppenParameter):

    def __init__(self):
        super().__init__()
        self.area_of_interest = [*range(29, 30+1)]
