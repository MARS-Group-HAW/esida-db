from esida.copernicus_parameter import CopernicusParameter

class copernicus_herbveg(CopernicusParameter):

    def __init__(self):
        super().__init__()

        self.area_of_interest = [
            'herbaceous_wetland',
        ]
