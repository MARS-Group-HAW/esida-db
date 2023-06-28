import functools
import osmnx as ox
from osmnx import io

from esida.parameter import BaseParameter

class osm_graph(BaseParameter):

    @functools.cached_property
    def is_loaded(self):
        return None

    def load(self, shapes=None, save_output=False):
        ox.settings.log_console=True
        ox.settings.use_cache=True
        ox.settings.cache_folder=self.get_data_path()
        ox.settings.timeout = 1800

        for shape in shapes:
            G = ox.graph_from_polygon(
                shape['geometry'],
                network_type='drive',
                simplify=True
            )

            #io.save_graph_shapefile(G, self.get_output_path() / f"{self.parameter_id}/graph.shp")

            # save graph nodes and edges to disk as GeoJSON
            # no direct API in OSMNx but maintainer has provided the following
            # snippet: https://github.com/gboeing/osmnx/issues/622
            gdf_nodes, gdf_edges = ox.graph_to_gdfs(G)
            gdf_nodes = ox.io._stringify_nonnumeric_cols(gdf_nodes)
            gdf_edges = ox.io._stringify_nonnumeric_cols(gdf_edges)


            # make sure output directory exitsts
            (self.get_output_path() / self.parameter_id).mkdir(parents=True, exist_ok=True)

            gdf_nodes.to_file(self.get_output_path() / self.parameter_id /'nodes.geojson', driver='GeoJSON')
            gdf_edges.to_file(self.get_output_path() / self.parameter_id / 'edges.geojson', driver='GeoJSON')


