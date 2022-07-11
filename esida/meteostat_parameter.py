import datetime as dt
from pathlib import Path
from urllib.parse import urlparse

import geopandas
import numpy as np
import fiona
import pandas as pd
from meteostat import Stations, Daily, Hourly

from esida.parameter import BaseParameter
from dbconf import get_engine, connect, close

class MeteostatParameter(BaseParameter):

    def __init__(self):
        super().__init__()

        self.time_col = 'date'
        self.meteo_mode = 'daily' # do we need daily or hourly data?
        self.col_of_interest = None

        # Meteostat can't handle Path() object
        Stations.cache_dir = self.get_data_path().as_posix()
        Daily.cache_dir = self.get_data_path().as_posix()
        Hourly.cache_dir = self.get_data_path().as_posix()

    def get_data_path(self) -> Path:
        """ Overwrite parameter_id based input directory, because we have
        multiple derived parameters from this source. """
        return Path(f"./input/data/meteostat/")

    def extract(self):
        stations = Stations()
        stations = stations.region('TZ')

        df = stations.fetch()

        # Meteostat ID is not always numerical. Safe the internal Meteostat ID
        # but add an numerical index for smooth PostGis access
        df['meteostat_id'] = df.index
        df.insert(0, 'meteostat_id', df.pop('meteostat_id')) # move meteostat ID to second column (directly ≤after index)

        df['id'] = range(1, len(df)+1)
        df.insert(0, 'id', df.pop('id'))

        gdf = geopandas.GeoDataFrame(
            df, geometry=geopandas.points_from_xy(df.longitude, df.latitude))

        gdf.to_postgis("meteostat_stations", get_engine(), if_exists='replace')


        # loop over all stations and collect daily values
        today = dt.date.today()
        start = dt.datetime(2010, 1, 1)
        end = dt.datetime(today.year, today.month, today.day)

        dfs_daily = []
        dfs_hourly = []

        for _, row in gdf.iterrows():
            # daily
            self.logger.debug("Fetching Daily %s (%s)", row['name'], row['meteostat_id'])
            data = Daily(row['meteostat_id'], start, end)
            data = data.fetch()

            self.logger.debug("Found Daily %s rows", len(data))
            data['meteostat_station_id'] = row['id']
            dfs_daily.append(data)

            # hourly
            self.logger.debug("Fetching Hourly %s (%s)", row['name'], row['meteostat_id'])
            data = Hourly(row['meteostat_id'], start, end)
            data = data.fetch()

            self.logger.debug("Found Hourly %s rows", len(data))
            data['meteostat_station_id'] = row['id']
            dfs_hourly.append(data)

        merged_df = pd.concat(dfs_daily)
        merged_df.to_sql("meteostat_data", get_engine(), if_exists='replace')

        merged_df = pd.concat(dfs_hourly)
        merged_df.to_sql("meteostat_hourly", get_engine(), if_exists='replace')


    def get_station_data_for_shape(self, shape):

        # load all stations
        stations_gdf = geopandas.read_postgis('SELECT * FROM meteostat_stations',
                                    con=connect(), geom_col='geometry')

        # get all stations inside shape
        gdfx = stations_gdf[stations_gdf.within(shape)].reset_index(drop=True)

        # no station inside shape. find nearest from centroid of shape
        if len(gdfx) == 0:
            sql = f"SELECT * FROM meteostat_stations ORDER BY st_distance( \
                ST_SetSRID(meteostat_stations.geometry, 4326), \
                ST_SetSRID(ST_GeomFromText('{str(shape.centroid)}'), 4326) ) ASC LIMIT 1"

            gdfx = geopandas.read_postgis(sql,
                                    con=connect(), geom_col='geometry')

        station_ids = list(gdfx['id'].unique())

        self.logger.debug("Found stations: %s", ','.join(map(str, station_ids)))

        if len(station_ids) == 0:
            self.logger.warning("No stations found for shape")

            return pd.DataFrame()

        dfxs = []
        for sid in station_ids:

            column = 'meteostat_data'
            if self.meteo_mode == 'hourly':
                column = 'meteostat_hourly'

            dfxs.append(pd.read_sql('SELECT * FROM ' + column + ' \
                WHERE meteostat_station_id = ' + str(sid), con=connect()))

        df = pd.DataFrame()
        if len(dfxs) == 1:
            df = dfxs[0]
        else:
            df = dfxs[0]
            for i in range(1, len(dfxs)):
                df = df.merge(dfxs[i], how='outer', on='time')

        if len(df) == 0:
            self.logger.warning("No data found for stations inside shape")


        return df

    def load(self, shapes=None, save_output=False):

        dfns = []

        if shapes is None:
            shapes = self._get_shapes_from_db()

        for shape in shapes:
            if "geometry" in shape:
                mask = [shape['geometry']]
            elif "file" in shape:
                with fiona.open(shape['file'], "r") as shapefile:
                    mask = [feature["geometry"] for feature in shapefile]
            else:
                raise ValueError("No geometry found for given shape.")

            df = self.get_station_data_for_shape(mask[0])

            if len(df) == 0:
                self.logger.warning("No data found for shape with id %s", shape['id'])
                continue

            # copying to new dataframe might trigger warning, regarding modifying
            # the copy of a dataframe, that is not the case here
            pd.options.mode.chained_assignment = None  # default='warn'

            dfn = self.consume(df, shape)

            dfns.append(dfn)

        self.df = pd.concat(dfns)

        self.save()

    def consume(self, df, shape):
        filter_col = [col for col in df if col.startswith(self.col_of_interest)]

        dfn = df[['time']]
        dfn = dfn.rename(columns={'time': 'date'})
        dfn['shape_id'] = shape['id']

        dfn[f'{self.parameter_id}']       = df[filter_col].mean(axis=1)
        dfn[f'{self.parameter_id}_std']   = df[filter_col].std(axis=1)
        dfn[f'{self.parameter_id}_min']   = df[filter_col].min(axis=1)
        dfn[f'{self.parameter_id}_max']   = df[filter_col].max(axis=1)
        dfn[f'{self.parameter_id}_count'] = df[filter_col].count(axis=1)

        dfn = dfn[dfn[f'{self.parameter_id}'].notna()]

        return dfn
