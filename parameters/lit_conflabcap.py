import pandas as pd

from esida.parameter import BaseParameter

from dbconf import get_engine

class lit_conflabcap(BaseParameter):

    def __init__(self):
        super().__init__()

    def extract(self):
        # Nothing to do here, manually prepared excel file.
        pass

    def load(self, shapes=None, save_output=False):
        countries_df = pd.read_sql("SELECT id, name FROM shape WHERE type='country'", con=get_engine())
        rows = []

        for _, row in countries_df.iterrows():
            if row['name'] == 'Tanzania':
                rows.append({
                    'shape_id': row['id'],
                    'year': 2023,
                    f'{self.parameter_id}': True
                })
            else:
                self.logger.warning("Country not available.")

        self.df = pd.DataFrame(rows)
        self.save()
