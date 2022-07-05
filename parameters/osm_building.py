import osmnx as ox

from esida.parameter import BaseParameter

class osm_building(BaseParameter):


    def load(self, shapes=None, save_output=False):
        ox.settings.log_console=True
        ox.settings.use_cache=True
        ox.settings.cache_folder=self.get_data_path()

        for shape in shapes:
            gdf = ox.geometries_from_polygon(
                shape['geometry'],
                {
                    'building': True
                }
            )

            # make sure output directory exists
            (self.get_output_path() / self.parameter_id).mkdir(parents=True, exist_ok=True)

            # this triggers exception
            #gdf.to_file(self.get_output_path() / self.parameter_id /'landuse.geojson', driver="GeoJSON")

            with open(self.get_output_path() / self.parameter_id / "building.geojson", "w") as text_file:
                text_file.write(gdf.to_json())
