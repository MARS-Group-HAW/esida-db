from esida.copernicus_parameter import CopernicusParameter

class copernicus_sparse(CopernicusParameter):

    def __init__(self):
        super().__init__()

        self.area_of_interest = [
            'bare_sparse_vegetation',
        ]
