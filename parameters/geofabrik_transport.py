import os
import subprocess
from urllib.parse import urlparse
from pathlib import Path

import geopandas
import pandas as pd

from esida.parameter import BaseParameter

class geofabrik_transport(BaseParameter):


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


    def load(self, shapes=None, save_output=False):

        path = Path(f"./input/data/geofabrik_pois/")
        gdf = geopandas.read_file(path / 'gis_osm_transport_free_1.shp')

        if shapes is None:
            shapes = self._get_shapes_from_db()

        for shape in shapes:
            aoi_gdf = gdf[gdf.within(shape['geometry'])].reset_index(drop=True)

            stats = aoi_gdf['fclass'].value_counts().to_dict()

            row = {
                'year': 2022,
                'shape_id': shape['id']
            }

            large = 0

            for key, value in stats.items():
                row[f"{self.parameter_id}_{key}"] = value

                if key in ['bus_station', 'railway_station', 'airport']:
                    large += value

            row[f"{self.parameter_id}"] = large

            self.rows.append(row)

        self.save()
