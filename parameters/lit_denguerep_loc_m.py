from pathlib import Path
import datetime as dt

import pandas as pd

from esida.parameter import BaseParameter

class lit_denguerep_loc_m(BaseParameter):

    def __init__(self):
        super().__init__()

        self.time_col = 'date'
        self.date_picker = 'month'

    def get_data_path(self) -> Path:
        return Path("./input/data/lit_denguerep/")

    def extract(self):
        # Nothing to do here, manually prepared csv file.
        pass

    def load(self, shapes=None, save_output=False):

        rows = []
        df = pd.read_csv(self.get_data_path() / 'ESIDA_lit_denguerep_m.csv', sep=";")

        if shapes is None:
            shapes = self._get_shapes_from_db()

        for shape in shapes:

            dfx = df[(df['shape_type'] == shape['type']) & (df['shape_name'] == shape['name'])].reset_index()

            if len(dfx) == 0:
                self.logger.warning("No data found for shape %s", shape['name'])
                continue

            for _, row in dfx.iterrows():
                rows.append({
                    'shape_id': shape['id'],
                    'date': dt.date(int(row['year']), int(row['month']), 1),
                    f'{self.parameter_id}': bool(row['dengue_loc'])
                })

        self.df = pd.DataFrame(rows)
        self.save()
