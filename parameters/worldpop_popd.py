"""
Demographic	Population density


- tiff 1x1 km
- mean
- Annualy (2010-2020)
- [Worldpop](https://www.worldpop.org/project/categories?id=18)

"""

import re
import os
import numpy as np

from esida.tiff_parameter import TiffParameter

class worldpop_popd(TiffParameter):

    def extract(self):
        for year in range(2010, 2020+1):
            url = f"https://data.worldpop.org/GIS/Population_Density/Global_2000_2020_1km_UNadj/{year}/TZA/tza_pd_{year}_1km_UNadj.tif"
            self._save_url_to_file(url)


    def consume(self, file, band, shape):
        x = re.search(r'[0-9]+', os.path.basename(file))
        year = int(x[0])

        self.rows.append({
            f"{self.parameter_id}_mean":    np.nanmean(band),
            f"{self.parameter_id}_min":     np.nanmin(band),
            f"{self.parameter_id}_max":     np.nanmax(band),
            f"{self.parameter_id}_std_dev": np.nanstd(band),

            'year': year,
            'shape_id': shape['id']
        })
