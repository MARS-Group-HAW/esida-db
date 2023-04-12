import os
import re
from pathlib import Path

import numpy as np
import pandas as pd

from esida.tiff_parameter import TiffParameter
from dbconf import get_engine

class worldpop_poverty_cons125(TiffParameter):

    def __init__(self):
        super().__init__()
        self.is_percent = True
        self.data = {}

    def extract(self):
        """ Download needed files, since this is 7z archive and we don't want
        to clutter out container with many tools, and die actual files are
        not that large, we also have those files in the git repository"""
        pass
        #subprocess.check_output(['wget', 'https://data.worldpop.org/GIS/Development_and_health_indicators/Individual_countries/Poverty/TZA/80.7z', "-P", "./input/data/worldpop_poverty"])

    def get_parameter_path(self):
        return Path(f"./input/data/worldpop_poverty/")


    def get_tiff_files(self, param_dir):
        files_all = sorted([s for s in os.listdir(param_dir) if s.rpartition('.')[2] in ('tiff','tif')])
        files = []

        for f in files_all:
            if "125" in f:
                files.append(f)


        return files

    def consume(self, file, band, shape):
        x = re.search(r'^tza([0-9]{2})([a-z0-9]+)\.', os.path.basename(file))

        year = 2000 + int(x[1])
        key = f"{self.parameter_id}"

        if ('uncert' in x[2]):
            key = f"{self.parameter_id}_std"

        if shape['id'] not in self.data:
            self.data[shape['id']] = {'year': year }

        self.data[shape['id']][key] = np.nanmean(band)

    def save(self):
        df = pd.DataFrame.from_dict(self.data, orient='index')
        df['shape_id'] = df.index
        df.to_sql(self.parameter_id, get_engine(), if_exists="replace")
