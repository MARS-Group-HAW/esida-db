import re
import os
import subprocess
from urllib.parse import urlparse

import rasterio
import rasterio.mask
import fiona

import numpy as np
import pandas as pd

from esida.tiff_parameter import TiffParameter
from dbconf import get_engine

class malariaatlas_mortal(TiffParameter):

    def extract(self):
        urls = [
            "https://malariaatlas.org/wp-content/uploads/2022-gbd2020/Pf_Mortality.zip",
        ]

        for url in urls:

            self._save_url_to_file(url)

            # Check if file is already unzipped
            a = urlparse(url)
            file_name = os.path.basename(a.path)
            if os.path.isdir(self.get_data_path() / "Pf_Mortality"):
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

    def load(self, shapes=None, save_output=False, param_dir=None):
        param_dir = self.get_data_path() / "Pf_Mortality/Raster Data/Pf_Mortality_rate_rmean/"
        super().load(shapes, save_output, param_dir)


    def consume(self, file, band, shape):
        x = re.search(r'_([0-9]+)\.tif$', os.path.basename(file))
        year = int(x[1])

        self.rows.append({
            f"{self.parameter_id}":         np.nanmean(band),
            f"{self.parameter_id}_min":     np.nanmin(band),
            f"{self.parameter_id}_max":     np.nanmax(band),
            f"{self.parameter_id}_std_dev": np.nanstd(band),
            'year': year,
            'shape_id': shape['id']
        })
