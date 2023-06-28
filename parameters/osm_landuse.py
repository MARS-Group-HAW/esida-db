import functools

import osmnx as ox
from osmnx import io

from esida.parameter import BaseParameter

class osm_landuse(BaseParameter):

    @functools.cached_property
    def is_loaded(self):
        return None

    def load(self, shapes=None, save_output=False):
        ox.settings.log_console=True
        ox.settings.use_cache=True
        ox.settings.cache_folder=self.get_data_path()
        ox.settings.timeout = 1800

        for shape in shapes:
            gdf = ox.geometries_from_polygon(
                shape['geometry'],
                {
                    'landuse': True
                }
            )

            # make sure output directory exists
            (self.get_output_path() / self.parameter_id).mkdir(parents=True, exist_ok=True)

            # this triggers exception
            #gdf.to_file(self.get_output_path() / self.parameter_id /'landuse.geojson', driver="GeoJSON")

            with open(self.get_output_path() / self.parameter_id / "landuse.geojson", "w") as text_file:
                text_file.write(gdf.to_json())
