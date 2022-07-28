import os
import subprocess
from urllib.parse import urlparse

import geopandas
import pandas as pd

from esida.parameter import BaseParameter

from dbconf import get_engine

class fao_drought(BaseParameter):

    def __init__(self):
        super().__init__()
        self.time_col = 'date'
        self.is_percent = True
        self.is_percent100 = True

    def extract(self):
        url = "https://www.fao.org/giews/earthobservation/asis/data/country/TZA/MAP_ASI/DATA/ASI_Dekad_Season1_data.csv"
        self._save_url_to_file(url)


    def load(self, shapes=None, save_output=False):

        if shapes is None:
            shapes = self._get_shapes_from_db()

        shapes_df = pd.DataFrame(shapes)
        name_to_id = dict(zip(shapes_df.name, shapes_df.id))

        df = pd.read_csv(self.get_data_path() / 'ASI_Dekad_Season1_data.csv',
            parse_dates=['Date'])

        df2 = df[['Province', 'Date', 'Data']]
        df2= df2.rename(columns={'Province': 'name', 'Date': 'date', 'Data': 'fao_drought'})

        def get_id_for_name(name):
            return name_to_id[name]

        df2['shape_id'] = df2['name'].apply(get_id_for_name)
        df2 = df2.drop(columns=['name'])

        self.df = df2

        self.save()
