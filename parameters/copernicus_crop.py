import re
import os
import datetime as dt

import numpy as np

from esida.copernicus_parameter import CopernicusParameter


class copernicus_crop(CopernicusParameter):

    def __init__(self):
        super().__init__()

        self.area_of_interest = [
            'cropland'
        ]

    def consume(self, file, band, shape):
        x = re.search(r'([0-9]{4})', os.path.basename(file))
        year = int(x[1])

        total_cells = np.count_nonzero(~np.isnan(band))
        values, count = np.unique(band, return_counts=True)
        stats = dict(zip(values, count))

        aoi_cells = 0
        for key in self.area_of_interest:
            val = self.get_value_for_key(key)
            aoi_cells += stats[val]

        self.rows.append({
            'year': year,
            'shape_id': shape['id'],
            f'{self.parameter_id}':         aoi_cells / total_cells,
        })
