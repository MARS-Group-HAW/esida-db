"""
Elevation data

"""

import numpy as np

from esida.rcmrd_parameter import RcmrdParameter

class rcmrd_elev(RcmrdParameter):

    def consume(self, file, band, shape):
        self.rows.append({
            'year': 2018, # only on file for 2018
            'shape_id': shape['id'],
            f'{self.parameter_id}':         np.nanmean(band),
            f"{self.parameter_id}_min":     np.nanmin(band),
            f"{self.parameter_id}_max":     np.nanmax(band),
            f"{self.parameter_id}_std_dev": np.nanstd(band),
        })
