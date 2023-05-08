import os
import glob
from pathlib import Path

import geopandas
import pandas as pd

from dbconf import get_engine
from esida.parameter import BaseParameter

class tncen22_disp(BaseParameter):

    def get_data_path(self) -> Path:
        return Path("./input/data/tncen22/")

    def download(self, *args, **kwargs) -> pd.DataFrame:
        """ STATcompiler are only region based, so before we can load
        data we need to know, if we query a region (-> return directly) or
        if wie load a district. Then we need to query the parent region first.
        """

        return self.download_inferred(*args, **kwargs)

    def load(self, shapes=None, save_output=False):

        # load regions ids
        sql = "SELECT id, name FROM shape WHERE type IN('country', 'region')"
        gdf = pd.read_sql(sql, get_engine())
        name_to_id = dict(zip(gdf.name, gdf.id))

        def normalize_name(name):
            if name == 'Dar es Salaam':
                name = 'Dar-es-salaam'
            return name

        df = pd.read_csv(self.get_data_path() / 'health_facilities.csv', sep=";")
        df['region'] = df['region'].apply(normalize_name)

        rows = []

        for name, shape_id in name_to_id.items():
            dfx = df[df['region'] == name].reset_index()

            if len(dfx) == 0:
                self.logger.info(f"Region {name} is not in data set.")
                continue

            rows.append({
                'year': 2022,
                'shape_id': shape_id,
                f"{self.parameter_id}": int(dfx.at[0, 'dispensary'])
            })

        self.df = pd.DataFrame(rows)
        self.save()
