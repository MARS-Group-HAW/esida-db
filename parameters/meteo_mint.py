from esida.meteostat_parameter import MeteostatParameter
from dbconf import get_engine

class meteo_mint(MeteostatParameter):

    def __init__(self):
        super().__init__()
        self.col_of_interest = 'tmin'

