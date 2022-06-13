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

RESOLUTION = "p05" # p04 or p25 resolution in deg
BASE_URL = "https://data.chc.ucsb.edu/products/CHIRPS-2.0/africa_daily/tifs/{resolution}/{year}/chirps-v2.0.{year}.{month:02d}.{day:02d}.tif.gz"


class chirps_tprecit(TiffParameter):

    def __init__(self):
        super().__init__()
        self.manual_nodata = -9999

    def extract(self):
        start_date = dt.date(2018, 1, 1)
        end_date = dt.date(2022, 4, 30)

        # download all required files
        for date in self.date_range(start_date, end_date):
            url = BASE_URL.format(resolution=RESOLUTION, year=date.year, month=date.month, day=date.day)

            if not self._save_url_to_file(url):
                # if file could not be downloaded, try to download without
                # .gz extension. For 2021-12-* all files are uncompressed
                self._save_url_to_file(url.replace("tif.gz", 'tif'))

        # after, gzip all downloaded *.gz files
        # only keep extracted files
        try:
            # cmd syntax didn't work, not sure why
            #subprocess.check_output('gzip -d ./input/data/chc_chirps/*.gz', shell=True)
            subprocess.run(f"gzip -d {self.get_data_path()}/*.gz", shell=True,
                capture_output=True, check=True)
        except subprocess.CalledProcessError as error:
            self.logger.warning("Could not unzip files: %s", error.stderr)

    def date_range(self, start_date, end_date):
        for n in range(int((end_date - start_date).days)):
            yield start_date + dt.timedelta(n)


    def _save_url_to_file(self, url) -> bool:
        """ Downloads a URL to be saved on the parameter data directory.
        Checks if file has already been downloaded. """
        a = urlparse(url)
        file_name = os.path.basename(a.path)

        if os.path.isfile(self.get_data_path() / file_name):
            self.logger.debug("Skipping b/c already downloaded %s", url)
            return True

        # does unzipped file exists?
        if os.path.isfile(self.get_data_path() / file_name.replace('.tif.gz', '.tif')):
            self.logger.debug("Skipping b/c already downloaded %s", url)
            return True

        try:
            subprocess.check_output(['wget', url, "-P", self.get_data_path().as_posix()])
            return True
        except subprocess.CalledProcessError as error:
            self.logger.warning("Could not download file: %s, %s", url, error.stderr)

        return False

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

    def download(self, shape_id, start=None, end=None):
        """ Overwrite download for CHIRPS data since the static/download parameters
        have a yearly resolution, but CHIRPS has daily. """
        return pd.DataFrame

    def get_fields(self, only_numeric=False):
        return []
