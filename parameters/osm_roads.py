import datetime as dt

import pandas as pd
import osmnx as ox
import geopandas
import fiona

from esida.parameter import BaseParameter
from dbconf import get_engine

class osm_roads(BaseParameter):

    def __init__(self):
        super().__init__()

        # table name for the cleaned records
        # can not be osm_airports. this name is used for the parameter!
        # but we want to store queried POIs as well
        self.table_name = f'data_{self.parameter_id}'

    def extract(self):
        ox.settings.log_console=True
        ox.settings.use_cache=True
        ox.settings.cache_folder=self.get_data_path()
        ox.settings.timeout = 1800

        # get convex hull for all loaded shapes, and query all airports for the
        # resulting convex hull polygon
        shp = self._get_convex_hull_from_db()

        G = ox.graph_from_polygon(
            shp,
            simplify=True,
            retain_all=True,
            custom_filter='["highway"~"trunk|primary|secondary"]'
        )

        gdf_nodes, gdf_edges = ox.graph_to_gdfs(G)
        gdf_nodes = ox.io._stringify_nonnumeric_cols(gdf_nodes)
        gdf_edges = ox.io._stringify_nonnumeric_cols(gdf_edges)

        # flatten MultiIndex created by OSMnx
        gdf = gdf_edges.reset_index(drop=True)

        # drop all columns where each row is NULL
        gdf = gdf.dropna(axis=1,how='all')

        gdf.to_postgis(self.table_name, con=get_engine(), if_exists='replace')

    def load(self, shapes=None, save_output=False):

        if shapes is None:
            shapes = self._get_shapes_from_db()

        # load imported airports
        df = geopandas.read_postgis(f"SELECT * FROM {self.table_name}",
                            geom_col='geometry', con=get_engine())

        dfs = []

        for shape in shapes:
            self.logger.debug("loading shape: %s", shape['name'])

            if "geometry" in shape:
                mask = [shape['geometry']]
            elif "file" in shape:
                with fiona.open(shape['file'], "r") as shapefile:
                    mask = [feature["geometry"] for feature in shapefile]
            else:
                raise ValueError("No geometry found for given shape.")

            # clip to only POIs within area of interest
            dfx = df[df['geometry'].within(mask[0])]

            # group / count matching facilities per year
            risk_score = 1
            if len(dfx) > 0:
                risk_score = 3

            dfs.append({
                'shape_id': shape['id'],
                'year': dt.datetime.now().year,
                self.parameter_id: risk_score
            })

        dfsx = pd.DataFrame(dfs)
        dfsx.to_sql(self.parameter_id, con=get_engine(), if_exists='replace')
