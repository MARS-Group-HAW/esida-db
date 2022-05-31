"""
Demographic	Population counts


- tiff 100 x 100 m
- sum total number
- Annualy (2010-2020)
- [Worldpop](https://www.worldpop.org/geodata/listing?id=69)

"""

import rasterio
import rasterio.mask
import fiona
import re
import os
import numpy as np
import pandas as pd

from esida.tiff_parameter import TiffParameter
from dbconf import get_engine

class worldpop_popc(TiffParameter):

    def extract(self):
        for year in range(2010, 2020+1):
            url = f"https://data.worldpop.org/GIS/Population/Global_2000_2020/{year}/TZA/tza_ppp_{year}_UNadj.tif"
            self._save_url_to_file(url)

    def consume(self, file, band, shape):
        x = re.search(r'[0-9]+', os.path.basename(file))
        year = int(x[0])

        self.rows.append({
            f"{self.parameter_id}_sum": np.nansum(band),
            'year': year,
            'shape_id': shape['id']
        })
