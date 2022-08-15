import re
import os
import subprocess
from pathlib import Path
from urllib.parse import urlparse

import numpy as np

from esida.tiff_parameter import TiffParameter

class malariaatlas_mortal(TiffParameter):

    def __init__(self):
        super().__init__()
        self.precision = None # to small value for rounding

    def extract(self):
        urls = [
            "https://malariaatlas.org/wp-content/uploads/2022-gbd2020/Pf_Mortality.zip",
        ]

        for url in urls:

            self._save_url_to_file(url)

            # Check if file is already unzipped
            a = urlparse(url)
            file_name = os.path.basename(a.path)
            if os.path.isdir(self.get_parameter_path() / "Pf_Mortality"):
                self.logger.debug("File already unzipped.")
                return
            try:
                # cmd syntax didn't work, not sure why
                #subprocess.check_output('gzip -d ./input/data/chc_chirps/*.gz', shell=True)
                in_file = self.get_parameter_path() / file_name
                out_dir = self.get_parameter_path().as_posix()
                subprocess.run(f'unzip {in_file} -d {out_dir}', shell=True,
                    capture_output=True, check=True)
            except subprocess.CalledProcessError as error:
                self.logger.warning("Could not unzip files: %s", error.stderr)

    def get_data_path(self) -> Path:
        return self.get_parameter_path() / "Pf_Mortality/Raster Data/Pf_mortality_rate_rmean/"

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
