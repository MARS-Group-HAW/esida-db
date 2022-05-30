import fiona
import geopandas
import pandas as pd

from dbconf import get_engine
from esida.thfr_parameter import ThfrParameter

class thfr_lab(ThfrParameter):

    def __init__(self):
        super().__init__()

        self.facility_types = [
            'Level IA2 (Dispensary Laboratory)',
            'Level III Single purpose Health Laboratory',
            'Level III Multipurpose Health Laboratory',
            'Level IA1 (Health Center Laboratory)',
            'Level IIA2 (District Laboratory)',
        ]
