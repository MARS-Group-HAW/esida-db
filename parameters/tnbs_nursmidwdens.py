from pathlib import Path

import pandas as pd

from esida.parameter import BaseParameter

from dbconf import get_engine

class tnbs_nursmidwdens(BaseParameter):

    def __init__(self):
        super().__init__()

    def get_data_path(self) -> Path:
        return Path("./input/data/tnbs_disthealthworkers/")

    def extract(self):
        # Nothing to do here, manually prepared excel file, extracted from
        # 2012 census
        pass

    def load(self, shapes=None, save_output=False):

        # load regions ids
        sql = "SELECT id, name FROM shape WHERE type IN('region')"
        gdf = pd.read_sql(sql, get_engine())
        name_to_id = dict(zip(gdf.name, gdf.id))

        def normalize_name(name):
            if name == 'Dar-es-salaam':
                name = 'Dar es salaam'

            # Songwe was created in 2016 and was part of Mbeya at the time
            # of the data curation (2014). So we assume the value there es well.
            if name == "Songwe":
                name = "Mbeya"

            return name.upper()

        # load data
        df = pd.read_csv(self.get_data_path() / 'Distribution of health workers densities.csv')

        rows = []

        for name, shape_id in name_to_id.items():

            df_name = normalize_name(name)

            if df_name not in df.columns:
                self.logger.info(f"{name} ({df_name}) not in data set.")
                continue

            dfx = df[df['HEALTH WORKERS'].isin([
                'DENSITY OF NURSES AND MIDWIVES PER 10000 POPULATION (EXCLUDING NURSING OFFICERS AND ASSISTANT NURSING OFFICER)'
            ])]

            for _, row in dfx.iterrows():
                rows.append({
                    'year': int(row['YEAR']),
                    'shape_id': shape_id,
                    f"{self.parameter_id}": row[df_name]
                })

        self.df = pd.DataFrame(rows)

        # load country to create mean, zanzibar zone has no values
        # so we assume the country mean for this area
        sql = "SELECT id, name FROM shape WHERE type IN('country') AND name ='Tanzania' LIMIT 1"
        gdf = pd.read_sql(sql, get_engine())
        name_to_id = dict(zip(gdf.name, gdf.id))

        rows.append({
            'year': 2014,
            'shape_id': gdf.at[0, 'id'],
            f"{self.parameter_id}": self.df[self.parameter_id].mean()
        })

        self.df = pd.DataFrame(rows)

        self.save()
