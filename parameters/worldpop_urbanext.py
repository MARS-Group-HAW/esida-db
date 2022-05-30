"""
Demographic	Population density


- tiff 1x1 km
- mean
- Annualy (2010-2020)
- [Worldpop](https://www.worldpop.org/project/categories?id=18)

"""

import os
import re
import numpy as np

from esida.tiff_parameter import TiffParameter

class worldpop_urbanext(TiffParameter):

    def extract(self):
        # bsgmi 2001 - 2013
        for year in range(2010, 2013+1):
            url = f"https://data.worldpop.org/GIS/Global_Settlement_Growth/Individual_countries/TZA/v0a/tza_bsgmi_v0a_100m_{year}.tif"
            self._save_url_to_file(url)

        # bsgme 2015 - 2020
        for year in range(2015, 2020+1):
            url = f"https://data.worldpop.org/GIS/Global_Settlement_Growth/Individual_countries/TZA/v0a/tza_bsgme_v0a_100m_{year}.tif"
            self._save_url_to_file(url)

    def consume(self, file, band, shape):
        x = re.search(r'[0-9]{4}', os.path.basename(file))
        year = int(x[0])

        total_cells = np.count_nonzero(~np.isnan(band))
        set_cells = np.count_nonzero(band == 1)

        self.rows.append({
            f"{self.parameter_id}_total_cells": total_cells,
            f"{self.parameter_id}_set_cells":   set_cells,
            f"{self.parameter_id}": set_cells / total_cells,

            'year': year,
            'shape_id': shape['id']
        })
