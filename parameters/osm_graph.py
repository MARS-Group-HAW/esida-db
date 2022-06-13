import osmnx as ox
from osmnx import io

from esida.parameter import BaseParameter

class osm_graph(BaseParameter):


    def load(self, shapes=None, save_output=False):
        ox.settings.log_console=True
        ox.settings.use_cache=True
        ox.settings.cache_folder=self.get_data_path()

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
            gdf_nodes.to_file(self.get_output_path() / self.parameter_id /'nodes.geojson', driver='GeoJSON')
            gdf_edges.to_file(self.get_output_path() / self.parameter_id / 'edges.geojson', driver='GeoJSON')


