import os
import importlib
from sys import platform
import datetime as dt
import logging
import subprocess
from pathlib import Path
from urllib.parse import urlparse
from typing import Optional, List


from sqlalchemy import text
from geoalchemy2.shape import to_shape
import pandas as pd
import geopandas
import shapely
import markdown
import isodate

from esida import shape_types
from esida.models import Shape
from dbconf import get_engine, connect

engine = get_engine()

docu_df = pd.read_csv('./input/meta_data/DB_Meta_Sheet - Documentation.csv')
docu_dict = docu_df[['Abbreviation', 'Category', 'Title', 'ESIDA database unit']].fillna('').set_index('Abbreviation').to_dict('index')

meta_dict = pd.read_csv('./input/meta_data/DB_Meta_Sheet - Metadata.csv').fillna('').rename(columns=str.lower).set_index('abbreviation').to_dict('index')

class BaseParameter():
    """ Base class for all parameters, implementing necessary functions. """

    def __init__(self):
        self.parameter_id = self.__class__.__name__
        self.rows = []
        self.df = None
        self.logger = logging.getLogger('root')

        self.output_path = Path(f"./output/{self.parameter_id}/")

        self.time_col = 'year'

        self.output = 'db'


        # In case the Data Layer stores some (vector) data as well, i.e.
        # raw data like POIs.
        # For concrete data layer this value should be set in the form of
        # `data_{parameter_id}`
        self.table_name = None


        # - quantity   (int, float)
        # - percent    0-1
        # - percent100 0-100
        # - binary     0,1
        self.type = None


        # How many decimal digits should be displayed?
        # Only used in UI for human on the web, API and CSV data are never rounded
        self.precision = 3

        # Is the parameter a percentage?
        self.is_percent = False

        # If true the value range for the percentage is 0 to 100 instead of
        # 0 to 1
        self.is_percent100 = False

        self.da_temporal_start = dt.datetime(2010, 1, 1)
        self.da_temporal_end   = dt.datetime(2020, 12, 31)


    def get_title(self) -> str:
        if self.parameter_id in docu_dict:
            if docu_dict[self.parameter_id ]['Title'] != '':
                return docu_dict[self.parameter_id ]['Title']
        return self.parameter_id

    def get_category(self) -> str:
        if self.parameter_id in docu_dict:
            return docu_dict[self.parameter_id ]['Category']
        return '-'

    def get_meta(self, key: str):
        if self.parameter_id in meta_dict and key in meta_dict[self.parameter_id]:
            return meta_dict[self.parameter_id][key]

        return ""

    def get_description(self) -> str:
        """ Get description / meta information of parameter as HTML formatted
        text. """

        # check meta data directory
        md_file = f"input/meta_data/{self.parameter_id}.md"
        if os.path.isfile(md_file):
            with open(md_file, encoding="utf-8") as fp:
                docblock = fp.read()

                # wrap parsed table inside Bootstrap .card for nicer formatting
                docmd = markdown.markdown(docblock, extensions=['tables'])
                docmd = docmd.replace('<table>', '<div class="card-body"><table class="table table-sm table-meta_data mb-0">')
                docmd = docmd.replace('</table>', '</table></div></div>')

                docmd = docmd.replace('<h2>', '<div class="card mb-3"><h5 class="card-header">')
                docmd = docmd.replace('</h2>', '</h5>')
        else:
            # docblock is fallback in case no md description is found
            pm = importlib.import_module(f'parameters.{self.parameter_id}')
            docblock = pm.__doc__ or "*please add docstring to module*"
            docmd = markdown.markdown(docblock, extensions=['tables'])

        return docmd

    def get_unit(self) -> str:
        if self.parameter_id not in docu_dict:
            return ""

        unit =  docu_dict[self.parameter_id ]['ESIDA database unit']

        if unit == 'percent':
            return '%'

        if unit == 'None':
            return ''

        return unit

    def get_parameter_path(self) -> Path:
        """ path to directory of parameter. """
        return Path(f"./input/data/{self.parameter_id}/")

    def get_data_path(self) -> Path:
        """ Path to data path, is most cases this is the parameter path, but
        in the case the parameter has som nested folders, this can be used
        to overrule the data path. """
        return self.get_parameter_path()

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

        if not os.path.exists(self.output_path):
            os.mkdir(self.output_path)

        return self.output_path

    def set_output_path(self, out_dir):
        self.output_path = out_dir

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
            self.df.to_csv(self.get_output_path() / f'{self.parameter_id}.csv', index=False)
        else:
            raise ValueError(f"Unknown save option {self.output}.")

    # ---

    def da_temporal_expected(self):
        if self.time_col == 'year':
            return self.da_temporal_end.year - self.da_temporal_start.year + 1
        elif self.time_col == 'date':
            return (self.da_temporal_end - self.da_temporal_start).days
        else:
            return None

    def da_count_temporal(self, shape_id=None):

        if not self.is_loaded():
            return None

        if self.time_col == 'year':
            sql = f"SELECT COUNT(*) FROM {self.parameter_id} WHERE  year >= {self.da_temporal_start.year} AND year <= {self.da_temporal_end.year}"
        elif self.time_col == 'date':
            sql = f"SELECT COUNT(*) FROM {self.parameter_id} WHERE date >= '{self.da_temporal_start}' AND date <= '{self.da_temporal_end}'"
        else:
            return None

        if shape_id:
            sql += f" AND shape_id = {int(shape_id)}"

        res = connect().execute(sql)
        return res.fetchone()[0]

    def da_temporal_date_first(self, shape_id=None):
        if not self.is_loaded():
            return None

        if self.time_col == 'year':
            sql = f"SELECT year FROM {self.parameter_id} WHERE 1=1"
            if shape_id:
                sql += f" AND shape_id = {int(shape_id)}"
            sql += " ORDER BY year ASC LIMIT 1"
        elif self.time_col == 'date':
            sql = f"SELECT date FROM {self.parameter_id} WHERE 1=1"
            if shape_id:
                sql += f" AND shape_id = {int(shape_id)}"
            sql += " ORDER BY date ASC LIMIT 1"

        res = connect().execute(sql)
        row = res.fetchone()
        if row:
            return str(row[0])
        else:
            return None

    def da_temporal_date_last(self, shape_id=None):
        if not self.is_loaded():
            return None

        if self.time_col == 'year':
            sql = f"SELECT year FROM {self.parameter_id} WHERE 1=1"
            if shape_id:
                sql += f" AND shape_id = {int(shape_id)}"
            sql += " ORDER BY year DESC LIMIT 1"
        elif self.time_col == 'date':
            sql = f"SELECT date FROM {self.parameter_id} WHERE 1=1"
            if shape_id:
                sql += f" AND shape_id = {int(shape_id)}"
            sql += " ORDER BY date DESC LIMIT 1"
        else:
            return None

        res = connect().execute(sql)
        row = res.fetchone()
        if row:
            return str(row[0])
        else:
            return None

    def da_temporal_date_first_dt(self):
        date = self.da_temporal_date_first()

        if self.time_col == 'year':
            return f"{date}-01-01"

        return date

    def da_temporal_date_last_dt(self):
        date = self.da_temporal_date_last()

        if self.time_col == 'year':
            return f"{date}-12-31"

        return date

    def da_temporal(self, shape_id=None):
        """ Determine temporal completeness of data source. """

        if not self.is_loaded():
            return None

        if self.time_col == 'year':
            should = self.da_temporal_end.year - self.da_temporal_start.year + 1
            sql = f"SELECT year FROM {self.parameter_id} WHERE  year >= {self.da_temporal_start.year} AND year <= {self.da_temporal_end.year}"
            if shape_id:
                sql += f" AND shape_id = {int(shape_id)}"
            sql += " GROUP BY year ORDER BY year"
            df = pd.read_sql(sql, con=connect())
            have = len(df)

            return have / should
        elif self.time_col == 'date':
            should = (self.da_temporal_end - self.da_temporal_start).days
            sql = f"SELECT date FROM {self.parameter_id} WHERE date >= '{self.da_temporal_start}' AND date <= '{self.da_temporal_end}'"
            if shape_id:
                sql += f" AND shape_id = {int(shape_id)}"
            sql += " GROUP BY date ORDER BY date"
            df = pd.read_sql(sql, con=connect())
            have = len(df)

            return have / should

        return None

    def da_spatial(self, shape_id=None):
        return None


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

    def temporal_steps(self,
            start: Optional[dt.datetime] = None,
            end:   Optional[dt.datetime] = None
        ) -> List[dt.datetime]:
        """ Gets all available temporal steps where the parameter has values. """

        sql = f"SELECT {self.time_col}"
        sql += f" FROM {self.parameter_id}"

        sql += " WHERE 1=1"

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

        sql += f' GROUP BY "{self.time_col}"'

        con = connect()
        res = con.execute(sql)
        steps = []
        for row in res:
            if self.time_col == 'year':
                steps.append(dt.datetime(row[0], 1, 1))
            elif self.time_col == 'date':
                steps.append(row[0])
            else:
                raise ValueError(f"Unknown time_col={self.time_col}")

        print(steps)

        return steps

    def download_inferred(self,
            shape_id=None,
            start: Optional[dt.datetime] = None,
            end: Optional[dt.datetime] = None,
            fallback_previous=False,
            fallback_parent=False) -> pd.DataFrame:
        """ Aggregates the download data, but in case there is now value available,
        for the shape in question, it will look for a parent shape """

        if shape_id is not None:
            shapes = [Shape.query.get(shape_id)]
        else:
            shapes = Shape.query.all()

        temporal_steps = self.temporal_steps(start, end)
        rows = []

        for shape in shapes:
            for step in temporal_steps:
                row = shape.get(self, fallback_parent=True, when=step)
                row.pop('index', None)
                row['shape_name'] = shape.name
                row['shape_type'] = shape.type

                # in case the value was inferred from a parent shape, the shape_id
                # is set to this shape, instead of the actual queried shape.
                # To be transparent in the output we "swap" the id back and keep
                # the inferred on.
                # The parameter ID is prefixed in case multiple downloads are merged,
                # so the column is unique.
                inferred_key = f'{self.parameter_id}_inferred_from_shape_id'
                row[inferred_key] = row['shape_id']
                row['shape_id'] = shape.id
                row[f'{self.parameter_id}_inferred'] = (row[inferred_key] != row['shape_id'])
                rows.append(row)

        print(len(rows))

        return pd.DataFrame(rows)


    def download(self,
            shape_id=None,
            start: Optional[dt.datetime] = None,
            end: Optional[dt.datetime] = None,
            fallback_previous=False) -> pd.DataFrame:
        """ Download all data for given shape id / all shapes. Will ONLY get
        the data stored in the table for the resp. parameter. """

        self.logger.debug("Downloading for shape_id=%s", shape_id)

        if not self.is_loaded():
            self.logger.warning("Download of data requested but not loaded for shape_id=%s", shape_id)
            return pd.DataFrame

        sql = f"SELECT {self.parameter_id}.*"

        sql += ", shape.name AS shape_name, shape.type AS shape_type"
        sql += f" FROM {self.parameter_id}"
        sql += f" JOIN shape ON ({self.parameter_id}.shape_id = shape.id)"

        sql += " WHERE 1=1"

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

        if fallback_previous:
            sql += f" ORDER BY {self.time_col} LIMIT 1"

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

    def get_map(self, shape_type, date):
        """ Get rows for given shape type and date. Contains shape geometry. """
        if not self.is_loaded():
            self.logger.warning("Download of data requested but not loaded for parameter_id=%s", self.parameter_id)
            return pd.DataFrame

        col = self.parameter_id

        sql =  f"SELECT {self.parameter_id}.{col} as value, shape.id, shape.name, shape.geometry"
        sql += f" FROM {self.parameter_id}"
        sql += f" JOIN shape ON shape.id = {self.parameter_id}.shape_id"
        sql += " WHERE 1=1"

        sql += " AND shape.type = %s"

        if self.time_col == 'year':
            sql += f" AND year = {date.year}"
        elif self.time_col == 'date':
            sql += f" AND date = '{str(date)}'"
        else:
            raise ValueError(f"Unknown time_col={self.time_col}")

        con = connect()
        res = con.execute(sql, (shape_type, ))
        rows = []
        for row in res:
            rows.append({
                'value': row[0],
                'shape_id': row[1],
                'name': row[2],
                'geometry':  shapely.wkb.loads(row[3], hex=True)
            })

        return rows

    def mean(self, shape_type: str) -> pd.DataFrame:

        sql = f"SELECT {self.time_col}, AVG({self.parameter_id}) as {self.parameter_id} FROM {self.parameter_id} \
        JOIN shape ON shape.id = {self.parameter_id}.shape_id \
        WHERE shape.type = %(type)s \
        GROUP BY {self.parameter_id}.{self.time_col}"

        df = pd.read_sql(sql, con=get_engine(), params={'type': shape_type})
        return df


    def peek(self, shape_id, when=None):
        """ Get the latest known value of the parameter, if available. """

        if not self.is_loaded():
            self.logger.warning("Peek of data requested but not loaded for shape_id=%s", shape_id)
            return None

        sql = f"SELECT dl.*, shape.type FROM {self.parameter_id} AS dl"

        sql += f" JOIN shape ON shape.id = dl.shape_id"


        sql += f" WHERE dl.shape_id = {shape_id}"



        if when is not None:
            if self.time_col == 'year':
                sql += f" AND dl.year = {when.year}"
            elif self.time_col == 'date':
                sql += f" AND dl.date = '{str(when)}'"
            else:
                raise ValueError(f"Unknown time_col={self.time_col}")

        sql += f" ORDER BY dl.{self.time_col} DESC LIMIT 1"



        con = connect()
        res = con.execute(sql)
        req = res.fetchone()



        if req is None:
            return None

        dreq =  dict(req)

        if self.parameter_id not in dreq:
            self.logger.error("Parameter column missing in peek for shape_id=%s", shape_id)
            return None

        if self.time_col not in dreq:
            self.logger.error("Time column missing in peek for shape_id=%s", shape_id)
            return None

        return dreq

    def years_with_data(self) -> List[int]:
        """ finds all years in which data are available. """

        if not self.is_loaded():
            self.logger.warning("Peek of data requested but not loaded for shape_id=%s", shape_id)
            return []

        if self.time_col == 'year':
            sql = f"SELECT DISTINCT year FROM  {self.parameter_id} ORDER BY year DESC"
        elif self.time_col == 'date':
            sql = f"SELECT DATE_PART('year', date ::date) AS year FROM {self.parameter_id} WHERE date is not NULL GROUP BY year ORDER BY year DESC"
        else:
            raise ValueError(f"Unknown time_col={self.time_col}")

        df = pd.read_sql(sql, con=get_engine())
        return df['year'].tolist()

    def format_value(self, value) -> str:

        if isinstance(value, (float)):
            if self.is_percent:
                if not self.is_percent100:
                    value = value * 100

            if self.precision is not None:
                value = round(value, self.precision)

        return value

    # ---

    def _get_shapes_from_db(self, shape_id=None):
        """ Fetch all available districts and regions from the database. """

        sql = "SELECT * FROM shape WHERE type IN %(types)s"
        params = {'types': tuple(shape_types())}

        if shape_id:
            sql = "SELECT * FROM shape WHERE id = %(shape_id)s"
            params = {'shape_id': shape_id }

        gdf = geopandas.GeoDataFrame.from_postgis(
            sql,
            get_engine(), geom_col='geometry', params=params)
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

    def _get_convex_hull_from_db(self):
        """ Creates the convex hull of all loaded shapes and returns it.

        Be aware that, the convex hull will include MORE area than the actual
        shapes. Nevertheless it is much faster than UNION/Dissolve of existing
        shapes. Since the function is usually called for extracting from a source
        and in the loading stage an individual mapping for shape/AOI is performed
        , this is not an issue.
        """

        sql = "SELECT ST_ConvexHull(ST_Collect(shape.geometry)) as geometry FROM shape"

        gdf = geopandas.GeoDataFrame.from_postgis(
            sql,
            get_engine(), geom_col='geometry')

        if len(gdf) == 0:
            raise ValueError("No shapes found in database.")

        return gdf.at[0, 'geometry']


    def _save_url_to_file(self, url, folder=None, file_name=None) -> bool:
        """ Downloads a URL to be saved on the parameter data directory.
        Checks if file has already been downloaded. Return True in case
        file was downloaded/was already downloaded, otherwise False.
        """
        a = urlparse(url)

        if file_name is None:
            file_name = os.path.basename(a.path)

        if folder is None:
            folder = self.get_parameter_path()

        if os.path.isfile(folder / file_name):
            self.logger.debug("Skipping b/c already downloaded %s", url)
            return True

        Path(folder).mkdir(parents=True, exist_ok=True)

        try:
            params = ['wget', "-O", folder / file_name, url]
            subprocess.check_output(params)
            return True
        except subprocess.CalledProcessError as error:
            # -O on wget will create the file regardless if it did exits and
            # could be downloaded. To don't have any empty files, we remove it
            if os.path.exists(folder / file_name):
                os.remove(folder / file_name)

            self.logger.warning("Could not download file: %s, %s", url, error.stderr)

        return False

    def has_log(self) -> bool:
        path = Path(self.get_output_path()/f"{self.parameter_id}.csv")
        return path.exists()

    def get_log_html(self):
        df = pd.read_csv(f'{self.get_output_path()}/{self.parameter_id}.csv',
        index_col=0)

        html =  df.to_html(index=True, classes="table table-sm", border=0, table_id='paramter-log')
        html = html.replace('text-align: right;', '')

        return html

    def op_min(self, signal, shape_id, *, value=None, start=None):
        start_date = signal.report_date
        end_date = signal.report_date

        if start:
            start_date = start_date - isodate.parse_duration(start)

        sql = f"SELECT COUNT(*) FROM {self.parameter_id} WHERE shape_id = {shape_id} "

        if self.time_col == 'year':
            sql += f" AND year >= {start_date.year}"
            sql += f" AND year <= {end_date.year}"
        elif self.time_col == 'date':
            sql += f" AND date >= '{str(start_date)}'"
            sql += f" AND date <= '{str(end_date)}'"
        else:
            raise ValueError(f"Unknown time_col={self.time_col}")

        sql +=  f" AND {self.parameter_id}.{self.parameter_id} < {value}"

        #print(sql)

        gdf = pd.read_sql(
            sql,
            get_engine())

        return len(gdf) > 0

    def op_lg(self, signal, shape_id, *, value=None, start=None, mode='all'):
        start_date = signal.report_date
        end_date = signal.report_date

        if start:
            start_date = start_date - isodate.parse_duration(start)

        df = self.download(shape_id, start_date, end_date)

        # No data available for signal date
        if len(df) == 0:
            df = self.download(shape_id, None, end_date, fallback_previous=True)

            if len(df) == 0:
                print("NO DATA!")
                return False, pd.DataFrame()



        if mode == 'all':
            print(df[self.parameter_id])
            dfx = df[df[self.parameter_id] > value]
            return (len(dfx) == len(df)), df

        if mode == 'mean':
           return df[self.parameter_id].mean() > value, df

        return False, pd.DataFrame()

        sql = f"SELECT COUNT(*) FROM {self.parameter_id} WHERE shape_id = {shape_id} "

        if self.time_col == 'year':
            sql += f" AND year >= {start_date.year}"
            sql += f" AND year <= {end_date.year}"
        elif self.time_col == 'date':
            sql += f" AND date >= '{str(start_date)}'"
            sql += f" AND date <= '{str(end_date)}'"
        else:
            raise ValueError(f"Unknown time_col={self.time_col}")

        sql +=  f" AND {self.parameter_id}.{self.parameter_id} > {value}"

        #print(sql)

        gdf = pd.read_sql(
            sql,
            get_engine())

        return len(gdf) > 0


    def has_raw_data(self):
        """ check if the raw data table name is set. """
        return self.table_name is not None

    def data_map(self):
        # This query uses ST_AsGeoJSON(t.*) to select a single row of a postgis
        # table as GeoJSON geometry. with the `*` all columns that are not the
        # geometry are read into the GeoJSONs properties.
        # With json_build_object() we aggregate the single Features from the rows
        # into a feature collection which we can directly use on a map, i.e.
        sql = f"""
        WITH data AS (
            SELECT ST_AsGeoJSON(t.*)::json as feature FROM {self.table_name} as t
        )
        SELECT
        json_build_object(
            'type', 'FeatureCollection',
            'features', json_agg(
            feature
            )
        ) AS geojson
        FROM data
        """

        res = connect().execute(sql)
        row = res.fetchone()
        if row:
            return row[0]
        else:
            return None
