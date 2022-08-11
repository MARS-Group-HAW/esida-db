"""
CHIRPS Data: https://www.chc.ucsb.edu/data/chirps

"""

import re
import os
import subprocess
import datetime as dt
from urllib.parse import urlparse

import numpy as np
import pandas as pd

from esida.tiff_parameter import TiffParameter


class chirts_mint(TiffParameter):

    def __init__(self):
        super().__init__()
        self.manual_nodata = -9999
        self.time_col = 'date'

    def extract(self):
        start_date = dt.date(2010, 1, 1)
        end_date = dt.date(2016, 12, 31) # last date available for data source

        base_url = 'http://data.chc.ucsb.edu/products/CHIRTSdaily/v1.0/global_tifs_p05/Tmin/{year}/Tmin.{year}.{month:02d}.{day:02d}.tif'
        tza_polygon = 'input/shapes/TZA-Rectangle/POLYGON.shp'

        # download all required files
        for date in self.date_range(start_date, end_date):
            url = base_url.format(year=date.year, month=date.month, day=date.day)
            self._save_url_to_file(url)

            a = urlparse(url)
            file_name = os.path.basename(a.path)

            path_orig = f"{self.get_data_path() / file_name}"
            path_tmp  = f"{self.get_data_path() / str('tmp' + file_name)}"

            # One file per day with 71mb would lead to ~26GB per year, and for
            # 6 years to ~155GB, to save storage and speed up the conumption
            # (I/O of reading the files), we crop the tiffs to the tanzania
            # region and delete the original files after downloading.
            try:
                subprocess.check_output([
                    'gdalwarp',
                    "-dstnodata", "-9999",

                    # input files
                    "-cutline", tza_polygon,
                    "-crop_to_cutline",

                    path_orig, # infile
                    path_tmp, # outfile
                ])

                subprocess.check_output([
                    'rm', path_orig
                ])

                subprocess.check_output([
                    'mv', path_tmp, path_orig
                ])

            except subprocess.CalledProcessError as error:
                self.logger.warning("Could not crop and mv file: %s, %s", url, error.stderr)

        #gdalwarp -dstnodata -9999 -cutline input/shapes/TZA-Rectangle/POLYGON.shp -crop_to_cutline input/data/chirts_maxt/Tmax.2010.01.02.tif input/data/chirts_maxt/Tmax.2010.01.02_tza.tmp.tif


    def date_range(self, start_date, end_date):
        for n in range(int((end_date - start_date).days)+1):
            yield start_date + dt.timedelta(n)

    def consume(self, file, band, shape):
        x = re.search(r'([0-9]{4})\.([0-9]{2})\.([0-9]{2})\.tif', os.path.basename(file))
        date = dt.date(int(x[1]), int(x[2]), int(x[3]))

        self.rows.append({
            'date': date,
            'shape_id': shape['id'],
            f'{self.parameter_id}':         np.nanmean(band),
            f"{self.parameter_id}_min":     np.nanmin(band),
            f"{self.parameter_id}_max":     np.nanmax(band),
            f"{self.parameter_id}_std_dev": np.nanstd(band),
        })
