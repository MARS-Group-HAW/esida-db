from esida.copernicus_parameter import CopernicusParameter

class copernicus_water(CopernicusParameter):

    def __init__(self):
        super().__init__()

        self.area_of_interest = [
            'permanent_inland_water',
        ]
