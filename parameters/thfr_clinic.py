import fiona
import geopandas
import pandas as pd

from dbconf import get_engine
from esida.thfr_parameter import ThfrParameter

class thfr_clinic(ThfrParameter):

    def __init__(self):
        super().__init__()

        self.facility_types = [
            'PolyClinic',
            'Optometry Clinic',
            'Medical Clinic'
        ]
