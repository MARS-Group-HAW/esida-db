from pathlib import Path
import pandas as pd

from esida.parameter import BaseParameter

from dbconf import get_engine

class lit_propseced_m(BaseParameter):

    def __init__(self):
        super().__init__()

    def extract(self):
        # Nothing to do here, manually prepared excel file.
        pass

    def get_data_path(self) -> Path:
        return Path('./input/data/lit_propseced')

    def load(self, shapes=None, save_output=False):
        rows = []
        data_df = pd.read_csv(self.get_data_path() / 'data.csv')

        # load data for regions
        regions_df = pd.read_sql("SELECT id, name FROM shape WHERE type='region'", con=get_engine())
        for _, row in regions_df.iterrows():

            dfx = data_df[data_df['Region'] == row['name']].reset_index()

            if len(dfx) != 1:
                self.logger.warning("Region not available in data %s", row['name'])
                continue

            rows.append({
                'shape_id': row['id'],
                'year': 2015,
                f'{self.parameter_id}': dfx.at[0, 'Male']
            })

        self.df = pd.DataFrame(rows)

        # set country to mean, so we have a value for the topmost level
        countries_df = pd.read_sql("SELECT id, name FROM shape WHERE type='country'", con=get_engine())

        for _, row in countries_df.iterrows():
            if row['name'] == 'Tanzania':
                rows.append({
                    'shape_id': row['id'],
                    'year': 2015,
                    f'{self.parameter_id}': self.df[self.parameter_id].mean()
                })
            else:
                self.logger.warning("Country not available.")

        self.df = pd.DataFrame(rows)
        self.save()
