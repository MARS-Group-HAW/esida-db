import os
import subprocess
from urllib.parse import urlparse

import geopandas
import pandas as pd

from esida.parameter import BaseParameter

from dbconf import get_engine

class who_hospbeddens(BaseParameter):


    def __init__(self):
        super().__init__()

    def extract(self):
        # Nothing to do here, manually prepared excel file.
        pass


    def load(self, shapes=None, save_output=False):
        gdf = geopandas.GeoDataFrame.from_postgis("SELECT * FROM shape WHERE type='country'",
            geom_col='geometry', con=get_engine())

        rows = []

        # https://www.who.int/data/gho/data/indicators/indicator-details/GHO/hospital-beds-(per-10-000-population)
        # download doesn't work, so we only copy the two values we need...
        for _, row in gdf.iterrows():

            if row['name'] == 'Tanzania':

                rows.append({
                    'shape_id': row['id'],
                    'year': 2006,
                    f'{self.parameter_id}': 11
                })

                rows.append({
                    'shape_id': row['id'],
                    'year': 2010,
                    f'{self.parameter_id}': 7
                })
            else:
                self.logger.warning("Country not available.")

        self.df = pd.DataFrame(rows)

        self.save()
