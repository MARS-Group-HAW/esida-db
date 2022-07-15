import os
import subprocess
from pathlib import Path
from urllib.parse import urlparse

from esida.parameter import BaseParameter

class GeofabrikParameter(BaseParameter):
    """ Extends BaseParameter class for Geofabrik file consumption. """

    def get_data_path(self) -> Path:
        """ Overwrite parameter_id based input directory, because we have
        multiple derived parameters from this source. """
        return Path("./input/data/geofabrik/")

    def extract(self):
        url  = "http://download.geofabrik.de/africa/tanzania-latest-free.shp.zip"
        self._save_url_to_file(url)

        # Check if file is already unzipped
        a = urlparse(url)
        file_name = os.path.basename(a.path)
        if os.path.isfile(self.get_data_path() / "README"):
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
