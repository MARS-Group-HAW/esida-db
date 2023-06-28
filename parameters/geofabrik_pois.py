import geopandas
import pandas as pd
import functools

from esida.geofabrik_parameter import GeofabrikParameter

class geofabrik_pois(GeofabrikParameter):

    @functools.cached_property
    def is_loaded(self):
        return None

    def load(self, shapes=None, save_output=False):
        pofw_gdf = geopandas.read_file(self.get_data_path() / 'gis_osm_pofw_free_1.shp')
        pofw_gdf['_src'] = 'pofw'

        pois_gdf = geopandas.read_file(self.get_data_path() /  'gis_osm_pois_free_1.shp')
        pois_gdf['_src'] = 'pois'

        gdf = pd.concat([pois_gdf, pofw_gdf], ignore_index=True)

        for shape in shapes:
            aoi_gdf = gdf[gdf.within(shape['geometry'])].reset_index(drop=True)
            aoi_gdf.to_file(self.get_output_path() / "geofabrik_pois.geojson", driver="GeoJSON")

