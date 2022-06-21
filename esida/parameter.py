import os
from sys import platform
import logging
import subprocess
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
import geopandas

from dbconf import get_engine, connect

engine = get_engine()

meta_df = pd.read_csv('./input/meta_data/DB_Meta_Sheet - Documentation.csv')

meta_dict = meta_df[['Abbreviation', 'Category', 'Title']].set_index('Abbreviation').to_dict('index')

class BaseParameter():
    """ Base class for all parameters, implementing necessary functions. """

    def __init__(self):
        self.parameter_id = self.__class__.__name__
        self.rows = []
        self.df = None
        self.logger = logging.getLogger('root')

        self.output_path = None

        self.time_col = 'year'

        self.output = 'db'

    def get_title(self) -> str:
        if self.parameter_id in meta_dict:
            return meta_dict[self.parameter_id ]['Title']
        return self.parameter_id

    def get_category(self) -> str:
        if self.parameter_id in meta_dict:
            return meta_dict[self.parameter_id ]['Category']
        return '-'

    def get_data_path(self) -> Path:
        return Path(f"./input/data/{self.parameter_id}/")

    def get_raw_data_size(self) -> int:
        """ get input data (raw data) size in bytes for parameter.
        depends on du cli utility so only works on linux systems.
        we use du for performance reasons, since collecting these stats with
        python would require looping over all the stored files. """
        if not self.get_data_path().exists():
            return 0

        if platform == "linux":
            return int(subprocess.check_output(['du', "-sb", self.get_data_path().as_posix()]).split()[0].decode('utf-8'))

        # du returns the amount of 512b chunks used by the file. So we need to
        # multiply with 512 to get the actual size in bytes.
        return int(subprocess.check_output(['du', "-s", self.get_data_path().as_posix()]).split()[0].decode('utf-8')) * 512


    def get_output_path(self) -> Path:

        if self.output_path is None:
            raise ValueError("You need to set the output path first.")

        return self.output_path

    def set_output_path(self, out_dir):
        if not os.path.exists(out_dir):
            os.mkdir(out_dir)
        self.output_path = out_dir
        #return Path(f"./output/{name}/{self.parameter_id}/")

    def get_fields(self, only_numeric=False):
        """ Check if the parameter has been loaded to the database. """
        sql = f"SELECT column_name, data_type \
            FROM information_schema.columns \
 WHERE table_schema = 'public' \
   AND table_name   = '{self.parameter_id}';"

        con = connect()
        res = con.execute(sql)
        fields = []
        for row in res:
            field = row[0]
            dtype = row[1]

            # if we want only numeric types for charts etc. filter out+
            # text based columns
            if only_numeric and dtype in ['text']:
                continue

            if field in ['index', 'year', 'date', 'shape_id']:
                continue

            fields.append(field)

        return fields


    def save(self):
        if self.df is None:
            self.df = pd.DataFrame(self.rows)

        if self.output == 'db':
            self.df.to_sql(self.parameter_id, get_engine(), if_exists='replace')
        elif self.output == 'fs':
            self.df.to_csv(self.get_output_path() / f'{self.parameter_id}.csv')
        else:
            raise ValueError(f"Unknown save option {self.output}.")


    # ---

    def extract(self):
        """ (E)xtract: automatic download of source files. """
        raise NotImplementedError

    def transform(self):
        """ (T)ransform: prepare data for loading. """
        raise NotImplementedError

    def load(self, save_output=False):
        """ (L)oad: consume/calculate data to insert into data warehouse. """
        raise NotImplementedError

    # ---

    def is_loaded(self) -> bool:
        """ Check if the parameter has been loaded to the database. """
        sql = f"SELECT EXISTS ( \
        SELECT FROM \
            pg_tables \
        WHERE \
            schemaname = 'public' AND \
            tablename  = '{self.parameter_id}' \
        );"

        con = connect()
        res = con.execute(sql)
        return res.fetchone()[0]


    def download(self, shape_id=None, start=None, end=None) -> pd.DataFrame:
        """ Download data for given shape id. """

        self.logger.debug("Downloading for shape_id=%s", shape_id)

        if not self.is_loaded():
            self.logger.warning("Download of data requested but not loaded for shape_id=%s", shape_id)
            return pd.DataFrame

        sql = f"SELECT * FROM {self.parameter_id} WHERE 1=1"

        if shape_id:
            sql += f" AND shape_id = {int(shape_id)}"

        if self.time_col == 'year':
            if start:
                sql += f" AND year >= {start.year}"
            if end:
                sql += f" AND year <= {end.year}"
        elif self.time_col == 'date':
            if start:
                sql += f" AND date >= '{str(start)}'"
            if end:
                sql += f" AND date <= '{str(end)}'"
        else:
            raise ValueError(f"Unknown time_col={self.time_col}")

        df = pd.read_sql_query(sql, con=get_engine())

        if len(df) == 0:
            self.logger.warning("Download of data requested, is loaded, but empty for shape_id=%s", shape_id)
            return df

        # all parameters tables have index and shape id columns, drop them
        # always so we don't duplicate them while merging the DataFrames
        drop_cols = ['index']
        if shape_id:
            drop_cols.append('shape_id')
        df = df.drop(drop_cols, axis=1, errors='ignore')


        return df
    # ---

    def _get_shapes_from_db(self):
        """ Fetch all available districts and regions from the database. """

        sql = "SELECT * FROM shape WHERE type IN('region', 'district')"
        #sql = "SELECT * FROM shape WHERE name = 'Mjini'"

        gdf = geopandas.GeoDataFrame.from_postgis(
            sql,
            get_engine(), geom_col='geometry')
        shapes = []
        for _, row in gdf.iterrows():
            shapes.append({
                'id':       row['id'],
                'name':     row['name'],
                'geometry': row['geometry'],
            })

        if len(shapes) == 0:
            raise ValueError("No shapes found in database.")

        return shapes


    def _save_url_to_file(self, url, folder=None) -> bool:
        """ Downloads a URL to be saved on the parameter data directory.
        Checks if file has already been downloaded. Return True in case
        file was downloaded/was already downloaded, otherwise False.
        """
        a = urlparse(url)
        file_name = os.path.basename(a.path)

        if folder is None:
            folder = self.get_data_path()

        if os.path.isfile(folder / file_name):
            self.logger.debug("Skipping b/c already downloaded %s", url)
            return True

        try:
            subprocess.check_output(['wget', url, "-P", folder])
            return True
        except subprocess.CalledProcessError as error:
            self.logger.warning("Could not download file: %s, %s", url, error.stderr)

        return False

