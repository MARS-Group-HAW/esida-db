import datetime as dt
from pathlib import Path
from urllib.parse import urlparse

import geopandas
import numpy as np
import pandas as pd
from meteostat import Stations, Daily

from esida.parameter import BaseParameter
from dbconf import get_engine

class MeteostatParameter(BaseParameter):

    def __init__(self):
        super().__init__()

        # Meteostat can't handle Path() object
        Stations.cache_dir = self.get_data_path().as_posix()
        Daily.cache_dir = self.get_data_path().as_posix()

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

        dfs = []

        for _, row in gdf.iterrows():
            self.logger.debug("Fetching %s (%s)", row['name'], row['meteostat_id'])
            data = Daily(row['meteostat_id'], start, end)
            data = data.fetch()

            self.logger.debug("Found %s rows", len(data))
            data['meteostat_station_id'] = row['id']
            dfs.append(data)

        merged_df = pd.concat(dfs)
        merged_df.to_sql("meteostat_data", get_engine(), if_exists='replace')


        def load(self):
            pass
