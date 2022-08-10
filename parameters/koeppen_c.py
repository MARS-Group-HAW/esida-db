from esida.koeppen_parameter import KoeppenParameter

class koeppen_c(KoeppenParameter):

    def __init__(self):
        super().__init__()
        self.area_of_interest = [*range(8, 16+1)]
