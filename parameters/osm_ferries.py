import datetime as dt

import pandas as pd
import osmnx as ox
import geopandas
import fiona

from esida.parameter import BaseParameter
from dbconf import get_engine

class osm_ferries(BaseParameter):

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

        # In OSM international airports can be tagged both ways with aerodrome, and/or
        # aerodrome:type = international
        # (see https://taginfo.openstreetmap.org/compare/aerodrome:type/aerodrome).
        # The actual value can be concatenated with other attributes as well,
        # like "civil;international". OSMnx seems to make a substring search though.
        gdf = ox.geometries_from_polygon(
            shp,
            {
                'amenity': "ferry_terminal"
            }
        )

        # flatten MultiIndex created by OSMnx
        gdf = gdf.reset_index(drop=True)

        # Some airports are stored as OSM ways/paths. But wie only want a POINT.
        # Centroid might be outside the polygon (runways), but still in the
        # airport vicinity, so this is Okay.
        # polygon -> centroid
        #
        # Use a projected CRS for the centroid, this maps the coordinate on a
        # flat map, instead of a geographic CRS which has earths curves in it.
        # -> projected CRS is will yield more accurate results.
        gdf['geometry'] = gdf['geometry'].to_crs('+proj=cea').centroid.to_crs(gdf.crs)

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
            present = 0
            if len(dfx) > 0:
                present = 1

            dfs.append({
                'shape_id': shape['id'],
                'year': dt.datetime.now().year,
                self.parameter_id: present
            })

        dfsx = pd.DataFrame(dfs)
        dfsx.to_sql(self.parameter_id, con=get_engine(), if_exists='replace')
