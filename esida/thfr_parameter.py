import os
import glob
from pathlib import Path

import datetime as dt
import pandas as pd
import geopandas
import fiona

from dbconf import get_engine
from esida.parameter import BaseParameter

class ThfrParameter(BaseParameter):
    """ Extends BaseParameter class for TZA Health Facility register function. """

    def __init__(self):
        super().__init__()

        self.stats = {
            'no_date': 0,
            'unix_0': 0,
            'malformed': 0,
            'future': 0,
            'valid': 0
        }

        self.facility_types = None

        # table name for the cleaned records
        self.table_name = 'thfr'

    # ---


    def get_data_path(self) -> Path:
        """ Overwrite parameter_id based input directory, because we have
        multiple derives parameters from this source. """
        return Path(f"./input/data/tza_hfr/")


    def extract(self):
        """ (E)xtract: automatic download of source files. """
        pass

    def transform(self):
        """ (T)ransform: prepare data for loading. """

        self.districts_gdf = geopandas.read_postgis("SELECT * FROM shape WHERE type = 'district'",
                        geom_col='geometry', con=get_engine())

        # latest download of tza hfr
        list_of_files = glob.glob(f'{self.get_data_path()}/*.xls')
        latest_file = max(list_of_files, key=os.path.getctime)

        # the xls file is actually just a HTML table
        # read_html() always returns a list, even if it's only one table in HTML
        df = pd.read_html(latest_file,
                    header=1, na_values=['Not Set', 'NIL', 'NOT documented', 'not documented'])[0]

        # clean up coordinates
        df['Latitude'] = df.apply(self.clean_lat, axis=1)
        df['Longitude'] = df.apply(self.cleat_lng, axis=1)
        df = df.apply(self.check_for_coord_pair, axis=1)

        # clean up opening date
        df['Date Opened'] = df.apply(self.parse_date, axis=1)

        gdf = geopandas.GeoDataFrame(
            df, geometry=geopandas.points_from_xy(df.Longitude, df.Latitude, crs="EPSG:4326"))

        gdf2 = gdf.apply(self.get_district_id_by_coord, axis=1)
        gdf['region_id'] = gdf2['region_id_by_coord']
        gdf['district_id'] = gdf2['district_id_by_coord']

        # write all to database that have coordinates inside tanzania
        final = gdf[gdf['region_id'].notna() & gdf['district_id'].notna()]
        final.to_postgis(self.table_name, con=get_engine(), if_exists='replace')


    def load(self, shapes=None, save_output=False):

        if shapes is None:
            shapes = self._get_shapes_from_db()

        # load all known facilities with types of interest
        df = geopandas.read_postgis(f"SELECT * FROM {self.table_name}",
                            geom_col='geometry', con=get_engine())
        df = df[df['Facility Type'].isin(self.facility_types)]

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

            if len(mask) != 1:
                self.logger.warning("Shape contains more than one geometry, using the first.")

            # clip to only facilities within area of interest
            dfx = df[df['geometry'].within(mask[0])]

            # group / count matching facilities per year
            tmpfx = self.count_hf_per_year(dfx, shape['id'])
            tmpfx[self.parameter_id] = tmpfx['total']
            dfs.append(tmpfx[['year', 'shape_id', self.parameter_id]])

        everything = pd.concat(dfs, ignore_index=True).reset_index(drop=True)
        everything.to_sql(self.parameter_id, con=get_engine(), if_exists='replace')

    def count_hf_per_year(self, hf_in_district_df, shape_id) -> pd.DataFrame:
        # amount w/o date
        without_opening_date = len(hf_in_district_df[hf_in_district_df['Date Opened'].isnull()])

        # only with date
        with_date_df = hf_in_district_df[hf_in_district_df['Date Opened'].notna()]
        with_date_df['year'] = with_date_df['Date Opened'].apply(lambda x: x.year)

        all_per_year_df = with_date_df.groupby('year').size().reset_index(name='count')
        all_per_year_df.index = pd.to_datetime(all_per_year_df['year'], format='%Y')

        all_per_year_df['total'] = all_per_year_df['count'].cumsum()
        all_per_year_df['total'] += without_opening_date

        all_per_year_df['shape_id'] = shape_id

        # reduce grouped index with duplicate column names
        all_per_year_df.index.names = ['date']

        return all_per_year_df



    # ---

    def is_transformed(self) -> bool:
        """ Check if the parameter has been loaded to the database. """
        sql = f"SELECT EXISTS ( \
        SELECT FROM \
            pg_tables \
        WHERE \
            schemaname = 'public' AND \
            tablename  = '{self.table_name}' \
        );"

        engine = get_engine()
        with engine.connect() as con:
            res = con.execute(sql)
            return res.fetchone()


    def clean_lat_lng(self, row, key):
        coord = row[key]

        # skip NaN
        if coord != coord:
            return None

        coord_str = str(coord).replace(' ', '')

        if False and coord_str[1] in ['.']:
            if coord_str[0] == 'S':
                return abs(float(coord_str[2:])) * -1
            elif coord_str[0] == 'E':
                return float(coord_str[2:])

        if False and coord_str[0] in ['S', 'E']:
            return float(coord_str[1:])

        try:
            c = float(coord)

            if (key == 'Latitude'):
                if (c > 90 or c < -90):
                    self.logger.warning("Latitude out of range (%s) for id=%s", coord, row['ID'])
                    return None
            elif (key == 'Longitude'):
                if (c > 180 or c < -180):
                    self.logger.warning("Longitude out of range (%s) for id=%s", coord, row['ID'])
                    return None
            return c
        except Exception as error:
            self.logger.warning("Malformed %s (%s) for id=%s: %s", key, coord, row['ID'], str(error))
            return None

    def clean_lat(self, row):
        return self.clean_lat_lng(row, 'Latitude')

    def cleat_lng(self, row):
        return self.clean_lat_lng(row, 'Longitude')

    def check_for_coord_pair(self, row):
        """ Make sure lat/lng are both set. """
        no_lat = False
        no_lng = False
        missing= ""
        if row['Latitude'] != row['Latitude']:
            missing += 'Latitude '
            no_lat = True

        if row['Longitude'] != row['Longitude']:
            missing += 'Longitude '
            no_lng = True

        if no_lat ^ no_lng:
            self.logger.warning(f"Missing one coordinate: {missing}for id={row['ID']}")
            row['Latitude'] = None
            row['Longitude'] = None

        return row

    def parse_date(self, row):
        date = row['Date Opened']

        # Skip NaN
        if date != date:
            self.stats['no_date'] += 1
            return pd.NaT

        # Skip timestamp=0
        if date == '1970-01-01':
            # is quite a lot...
            self.logger.warning(f"Date is set to Unix timestamp=0 for id={row['ID']}")
            self.stats['unix_0'] += 1
            return pd.NaT

        try:
            dtime = pd.to_datetime(date, format='%Y-%m-%d')

            if dtime > dt.datetime.now():
                self.stats['future'] += 1
                self.logger.warning(f"Date is in the future ({date}) for with state {row['Operating Status']} id={row['ID']}")
            else:
                self.stats['valid'] += 1
            return dtime

        except ValueError as e:
            self.logger.warning(f"Malformed date string ({date}) for id={row['ID']}")
            self.stats['malformed'] += 1
            return pd.NaT

    def get_district_id_by_coord(self, row):
        point = row['geometry']

        row['region_id_by_coord'] = None
        row['district_id_by_coord'] = None

        # ps.isna() etc WON'T catch an empty geometry from geopandas!
        if point.is_empty:
            return row

        match_district = self.districts_gdf[self.districts_gdf['geometry'].contains(point)].reset_index()

        if len(match_district) != 1:
            self.logger.warning(f"Could not match coordinate to district for id={row['ID']}")
            return row

        row['region_id_by_coord'] = match_district.at[0, 'parent_id']
        row['district_id_by_coord'] = match_district.at[0, 'id']

        return row
