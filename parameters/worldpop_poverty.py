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
import pandas as pd

from esida.tiff_parameter import TiffParameter
from dbconf import get_engine

class worldpop_poverty(TiffParameter):

    def __init__(self):
        super().__init__()
        self.data = {}

    def extract(self):
        """ Download needed files, since this is 7z archive and we don't want
        to clutter out container with many tools, and die actual files are
        not that large, we also have those files in the git repository"""
        pass
        #subprocess.check_output(['wget', 'https://data.worldpop.org/GIS/Development_and_health_indicators/Individual_countries/Poverty/TZA/80.7z', "-P", "./input/data/worldpop_poverty"])

    def consume(self, file, band, shape):
        x = re.search(r'^tza([0-9]{2})([a-z0-9-]+)\.', os.path.basename(file))
        year = 2000 + int(x[1])
        key = f"{self.parameter_id}_{x[2].replace('-', '')}"

        if shape['id'] not in self.data:
            self.data[shape['id']] = {'year': year }

        self.data[shape['id']][key]              = np.nanmean(band)
        #self.data[shape['id']][f"{key}_min"]     = np.nanmin(band)
        #self.data[shape['id']][f"{key}_max"]     = np.nanmax(band)
        #self.data[shape['id']][f"{key}_std_dev"] = np.nanstd(band)

    def save(self):
        df = pd.DataFrame.from_dict(self.data, orient='index')
        df['shape_id'] = df.index
        df.to_sql(self.parameter_id, get_engine(), if_exists="replace")
