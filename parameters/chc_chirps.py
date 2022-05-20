"""
CHIRPS Data: https://www.chc.ucsb.edu/data/chirps

"""

import logging
import subprocess
import rasterio
import re
import os
import numpy as np
import pandas as pd
from urllib.parse import urlparse
import datetime as dt

from dbconf import get_engine

parameter_id = 'chc_chirps'
logger = logging.getLogger('root')

RESOLUTION = "p05" # p04 or p25 resolution in deg
BASE_URL = "https://data.chc.ucsb.edu/products/CHIRPS-2.0/africa_daily/tifs/{resolution}/{year}/chirps-v2.0.{year}.{month:02d}.{day:02d}.tif.gz"


def is_loaded() -> bool:
    sql = f"SELECT EXISTS ( \
    SELECT FROM \
        pg_tables \
    WHERE \
        schemaname = 'public' AND \
        tablename  = '{parameter_id}' \
    );"

    engine = get_engine()

    with engine.connect() as con:
        # well this not good style...
        rs = con.execute(sql)
        return rs.fetchone()

    return False


def consume(file, district_id=None):
    x = re.search(r'([0-9]{4})\.([0-9]{2})\.([0-9]{2})\.tif', os.path.basename(file))
    date = dt.date(int(x[1]), int(x[2]), int(x[3]))

    dataset = rasterio.open(file)
    band1 = dataset.read(1, masked=True)

    # NoData meta attribute is not set on CHIRPS data
    # but nodata value is -9999 as usual for GeoTiffs
    band1[band1==-9999] = np.nan

    return {'value': np.nanmean(band1), 'date': date}

def to_sql(rows, engine):
    df = pd.DataFrame(rows)
    df.to_sql(parameter_id, engine)

def download(shape_id, engine):

    return pd.DataFrame

def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days)):
        yield start_date + dt.timedelta(n)

def extract():
    start_date = dt.date(2018, 1, 1)
    end_date = dt.date(2022, 12, 29)


    start_date = dt.date(2022, 1, 1)
    end_date = dt.date(2022, 1, 2)

    # download all required files
    for date in daterange(start_date, end_date):
        _download_file(date)

    # after, gzip all downloaded *.gz files
    # only keep extracted files
    try:
        # cmd syntax didn't work, not sure why
        #subprocess.check_output('gzip -d ./input/data/chc_chirps/*.gz', shell=True)
        subprocess.run('gzip -d ./input/data/chc_chirps/*.gz', shell=True,
            capture_output=True, check=True)
    except subprocess.CalledProcessError as error:
        logger.warning("Could not unzip files: %s", error.stderr)

def _download_file(date):

    url = BASE_URL.format(resolution=RESOLUTION, year=date.year, month=date.month, day=date.day)
    f = os.path.basename(url)

    # does zipped file exists?
    if os.path.isfile(f"./input/data/chc_chirps/{f}"):
        logger.debug("Skipping b/c already downloaded %s", url)
        return

    # does unzipped file exists?
    if os.path.isfile(f"./input/data/chc_chirps/{f.replace('.tif.gz', '.tif')}"):
        logger.debug("Skipping b/c already downloaded %s", url)
        return

    try:
        subprocess.check_output(['wget', url, "-P", "./input/data/chc_chirps"])
    except Exception as e:
        logger.warning("Could not download file: %s, %s", url, e)

