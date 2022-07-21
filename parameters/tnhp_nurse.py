import os
import glob

import geopandas
import pandas as pd

from dbconf import get_engine
from esida.tnhp_parameter import TnhpParameter

class tnhp_nurse(TnhpParameter):

    def load(self, shapes=None, save_output=False):

        # latest download of tza hfr
        list_of_files = glob.glob(f'{self.get_data_path()}/*.csv')
        if len(list_of_files) == 0:
            raise Exception("extract first")
        latest_file = max(list_of_files, key=os.path.getctime)

        sql = "SELECT * FROM shape WHERE type IN('region')"
        gdf = geopandas.GeoDataFrame.from_postgis(
            sql, get_engine(), geom_col='geometry')
        name_to_id = dict(zip(gdf.name, gdf.id))

        df = pd.read_csv(latest_file)

        def get_region_id_for_name(name):
            region_name = name.replace(' Region', '')

            if region_name == 'Dar Es Salaam':
                region_name = 'Dar-es-salaam'

            return name_to_id[region_name]

        df = df[df['function'] == 'Nurse'].reset_index(drop=True)

        df['shape_id'] = df['region'].apply(get_region_id_for_name)

        df[f"{self.parameter_id}"] = df['value']
        df = df.drop(columns=['region', 'function', 'value'])

        self.df = df
        self.save()
