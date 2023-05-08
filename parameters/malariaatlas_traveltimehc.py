import re
import os
import subprocess
from pathlib import Path
from urllib.parse import urlparse

import numpy as np

from esida.tiff_parameter import TiffParameter

class malariaatlas_traveltimehc(TiffParameter):

    def __init__(self):
        super().__init__()
        self.precision = 3 # to small value for rounding

    def extract(self):
        urls = [
            "https://data.malariaatlas.org/geoserver/Accessibility/ows?service=CSW&version=2.0.1&request=DirectDownload&ResourceId=Accessibility:202001_Global_Walking_Only_Travel_Time_To_Healthcare",
        ]

        for url in urls:

            print("wtd")
            print(url)
            self._save_url_to_file(url)

            # Check if file is already unzipped
            a = urlparse(url)
            file_name = os.path.basename(a.path)

            print(file_name)

            if os.path.isfile(self.get_parameter_path() / f"{file_name}.tif"):
                self.logger.debug("File already unzipped.")
                return
            try:
                # cmd syntax didn't work, not sure why
                #subprocess.check_output('gzip -d ./input/data/chc_chirps/*.gz', shell=True)
                in_file = self.get_parameter_path() / file_name
                out_dir = self.get_parameter_path().as_posix()
                print(f'unzip {in_file} -d {out_dir}')
                subprocess.run(f'unzip {in_file} -d {out_dir}', shell=True,
                    capture_output=True, check=True)
            except subprocess.CalledProcessError as error:
                self.logger.warning("Could not unzip files: %s", error.stderr)

    def consume(self, file, band, shape):
        x = re.search(r'_([0-9]+)\.tif$', os.path.basename(file))
        year = int(x[1])

        if shape['id'] in [242, 253, 205, 240, 194, 197, 217, 218, 252]:
            return

        self.rows.append({
            f"{self.parameter_id}":         np.nanmean(band),
            f"{self.parameter_id}_min":     np.nanmin(band),
            f"{self.parameter_id}_max":     np.nanmax(band),
            f"{self.parameter_id}_std_dev": np.nanstd(band),
            'year': year,
            'shape_id': shape['id']
        })
