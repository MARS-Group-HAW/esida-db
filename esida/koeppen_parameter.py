
import os
import re
import subprocess
from pathlib import Path
from urllib.parse import urlparse

import numpy as np

from esida.tiff_parameter import TiffParameter

class KoeppenParameter(TiffParameter):
    """ Extends TiffParameter class for Koeppen data consumption. """

    def __init__(self):
        super().__init__()
        self.is_percent = True

        # GeoTiff files hav no NoData set. But the value 0 is used for water
        # bodies and has no meaning for the climate zones. We use this as
        # NoData value.
        self.manual_nodata = 0

        self.area_of_interest = []


    def get_data_path(self) -> Path:
        """ Overwrite parameter_id based input directory, because we have
        multiple derives parameters from this source. """
        return Path(f"./input/data/koeppen/")

    def extract(self):
        url = 'https://figshare.com/ndownloader/files/12407516'

        if not os.path.isfile(self.get_data_path() / 'Beck_KG_V1.zip'):
            self._save_url_to_file(url, folder=self.get_data_path(), file_name="Beck_KG_V1.zip")

        if os.path.isfile(self.get_data_path() / "legend.txt"):
            self.logger.debug("File already unzipped.")
            return
        try:
            # cmd syntax didn't work, not sure why
            #subprocess.check_output('gzip -d ./input/data/chc_chirps/*.gz', shell=True)
            in_file = self.get_data_path() / "Beck_KG_V1.zip"
            out_dir = self.get_data_path().as_posix()
            subprocess.run(f'unzip {in_file} -d {out_dir}', shell=True,
                capture_output=True, check=True)
        except subprocess.CalledProcessError as error:
            self.logger.warning("Could not unzip files: %s", error.stderr)

    def get_tiff_files(self, param_dir):
        #files = sorted([s for s in os.listdir(param_dir) if s.rpartition('.')[2] in ('tiff','tif')])

        # only one file is of interest for us
        return ["Beck_KG_V1_present_0p0083.tif"]

    def consume(self, file, band, shape):
        total_cells = np.count_nonzero(~np.isnan(band))
        values, count = np.unique(band, return_counts=True)
        stats = dict(zip(values, count))

        aoi_cells = 0
        for key in self.area_of_interest:
            if key in stats:
                aoi_cells += stats[key]

        self.rows.append({
            'year': 2016,
            'shape_id': shape['id'],
            f'{self.parameter_id}': aoi_cells / total_cells,
        })
