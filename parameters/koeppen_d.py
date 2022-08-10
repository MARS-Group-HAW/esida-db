from esida.koeppen_parameter import KoeppenParameter

class koeppen_d(KoeppenParameter):

    def __init__(self):
        super().__init__()
        self.area_of_interest = [*range(17, 28+1)]
