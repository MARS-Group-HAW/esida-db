import re
import os
import subprocess
import datetime as dt
from urllib.parse import urlparse

import numpy as np
import pandas as pd

from esida.tiff_parameter import TiffParameter

class worldpop_sexage(TiffParameter):

    def __init__(self):
        super().__init__()
        self._tmp = {}
        self.ages = None

    def extract(self):
        base_url = 'https://data.worldpop.org/GIS/AgeSex_structures/Global_2000_2020/{year}/TZA/tza_{sex}_{age}_{year}.tif'

        for year in range(2010, 2020+1):
            for sex in ['f', 'm']:
                for age in [0, 1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80]:
                    url = base_url.format(year=year, age=age, sex=sex)
                    self._save_url_to_file(url)

    def get_tiff_files(self, param_dir):
        files = sorted([s for s in os.listdir(param_dir) if s.rpartition('.')[2] in ('tiff','tif')])

        return files



    def consume(self, file, band, shape):
        x = re.search(r'([fm]{1})_([0-9]{1,2})_([0-9]{4})\.tif', os.path.basename(file))
        sex  = x[1]
        age  = int(x[2])
        year = int(x[3])

        key = f"{year}_{shape['id']}"
        if key in self._tmp:
            self._tmp[key][f'{self.parameter_id}'] += np.nansum(band)
        else:
            self._tmp[key] = {
                'year': year,
                'shape_id': shape['id'],
                f'{self.parameter_id}': np.nansum(band)
            }

    def save(self):
        self.df = pd.DataFrame(self._tmp.values())
        super().save()
