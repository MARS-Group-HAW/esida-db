import os
import subprocess
from urllib.parse import urlparse

import geopandas
import pandas as pd

from esida.parameter import BaseParameter

class geofabrik_pois(BaseParameter):


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

        layers = [
            'pois',
            'pofw'
        ]


        pofw_gdf = geopandas.read_file(self.get_data_path() / 'gis_osm_pofw_free_1.shp')
        pofw_gdf['_src'] = 'pofw'

        pois_gdf = geopandas.read_file(self.get_data_path() /  'gis_osm_pois_free_1.shp')
        pois_gdf['_src'] = 'pois'

        gdf = pd.concat([pois_gdf, pofw_gdf], ignore_index=True)


        for shape in shapes:
            aoi_gdf = gdf[gdf.within(shape['geometry'])].reset_index(drop=True)
            aoi_gdf.to_file(self.get_output_path() / "geofabrik_pois.geojson", driver="GeoJSON")

