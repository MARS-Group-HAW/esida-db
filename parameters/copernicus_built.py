from esida.copernicus_parameter import CopernicusParameter

class copernicus_built(CopernicusParameter):

    def __init__(self):
        super().__init__()

        self.area_of_interest = [
            'built-up',
        ]
