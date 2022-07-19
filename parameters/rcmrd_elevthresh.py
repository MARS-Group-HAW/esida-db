"""
Elevation data

"""

import numpy as np

from esida.rcmrd_parameter import RcmrdParameter

class rcmrd_elevthresh(RcmrdParameter):

    def consume(self, file, band, shape):

        total_cells = np.count_nonzero(~np.isnan(band))
        cells_under_threshold = np.count_nonzero(band < 1600)

        band[band<1600] = np.nan

        self.rows.append({
            'year': 2018, # only on file for 2018
            'shape_id': shape['id'],
            f'{self.parameter_id}': cells_under_threshold / total_cells,
        })
