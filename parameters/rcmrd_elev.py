"""
Elevation data

"""

import os
import subprocess
from urllib.parse import urlparse
import numpy as np
import pandas as pd

from esida.tiff_parameter import TiffParameter
from dbconf import get_engine

class rcmrd_elev(TiffParameter):

    def extract(self):
        url = "https://s3.amazonaws.com/rcmrd-open-data/downloadable_files/Tanzania_SRTM30meters.zip"
        self._save_url_to_file(url)

        # Check if file is already unzipped
        a = urlparse(url)
        file_name = os.path.basename(a.path)
        if os.path.isfile(self.get_data_path() / file_name.replace(".zip", ".tif")):
            self.logger.debug("File already unzipped.")
            return

        try:
            # cmd syntax didn't work, not sure why
            #subprocess.check_output('gzip -d ./input/data/chc_chirps/*.gz', shell=True)
            in_file = self.get_data_path() / file_name
            out_dir = self.get_data_path().as_posix()
            subprocess.run(f'unzip {in_file} -d {out_dir}', shell=True,
                capture_output=True, check=True)
        except subprocess.CalledProcessError as error:
            self.logger.warning("Could not unzip files: %s", error.stderr)

    def consume(self, file, band, shape):
        self.rows.append({
            'year': 2018, # only on file for 2018
            'shape_id': shape['id'],
            f'{self.parameter_id}':         np.nanmean(band),
            f"{self.parameter_id}_min":     np.nanmin(band),
            f"{self.parameter_id}_max":     np.nanmax(band),
            f"{self.parameter_id}_std_dev": np.nanstd(band),
        })
