import fiona
import geopandas
import pandas as pd

from dbconf import get_engine
from esida.thfr_parameter import ThfrParameter

class thfr_hospital(ThfrParameter):

    def __init__(self):
        super().__init__()

        self.facility_types = [
            'Hospital at District Level',
            'District Hospital',
            'Regional Referral Hospital',
            'Hospital at Regional Level',
            'Hospital at Zonal Level',
            'National Super Specialized Hospital',
            'Zonal Referral Hospital',
            'National Hospital',
        ]
