import os
import subprocess
from urllib.parse import urlparse

import geopandas
import pandas as pd

from esida.parameter import BaseParameter

from dbconf import get_engine

class lit_dengue_out_loc(BaseParameter):


    def __init__(self):
        super().__init__()
        self.time_col = 'date'

    def extract(self):
        # Nothing to do here, manually prepared excel file.
        pass


    def load(self, shapes=None, save_output=False):
        df = pd.read_excel(self.get_data_path() / 'WHOAB_summary_withSignalSheet.xlsx', sheet_name=1,
                        na_values=['None', 'none'],
                        parse_dates=['Report date', 'Start date', 'End date'])

        regions_gdf = geopandas.GeoDataFrame.from_postgis("SELECT * FROM shape WHERE type='region'",
            geom_col='geometry', con=get_engine())
        regions = dict(zip(regions_gdf.name, regions_gdf.id))

        def get_id_for_name(name):
            if name not in regions:
                self.logger.warning("Unknown region: %s", name)
                return None
            return regions[name]

        # map textual regions to database
        df['shape_id'] = df['Regions'].apply(get_id_for_name)


        df = df.rename(columns={"Report date": "date"})
        df = df.drop(columns=['Regions'])

        # rename columns to match our naming scheme of <parameter_id>_<col>
        rename = {}
        for c in list(df.columns):
            if c in ['date', 'shape_id']:
                continue
            rename[c] = f"{self.parameter_id}_{c.lower().replace(' ', '_')}"
        self.df = df.rename(columns=rename)

        self.save()
