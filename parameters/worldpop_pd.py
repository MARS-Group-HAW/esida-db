"""
Demographic	Population density


- tiff 1x1 km
- mean
- Annualy (2010-2020)
- [Worldpop](https://www.worldpop.org/project/categories?id=18)

"""

import logging
import subprocess
import rasterio
import re
import os
import numpy as np
import pandas as pd
from urllib.parse import urlparse

parameter_id = 'worldpop_pd'
logger = logging.getLogger('root')

def consume(file):
    x = re.search(r'[0-9]+', os.path.basename(file))
    year = int(x[0])

    dataset = rasterio.open(file)
    band1 = dataset.read(1, masked=True)

    return {'value': np.nanmean(band1), 'year': year}

def to_sql(rows, engine):
    df = pd.DataFrame(rows)
    df.to_sql(parameter_id, engine)


def download(shape_id, engine):
    sql = "SELECT year, value as {} FROM {} WHERE district_id = {}".format(
        parameter_id, parameter_id,
        shape_id
    )

    df = pd.read_sql_query(sql, con=engine)

    return df


def completeness_start():
    return 2010

def completeness_end():
    return 2020

def extract():
    for year in range(2010, 2020+1):
        url = f"https://data.worldpop.org/GIS/Population_Density/Global_2000_2020_1km_UNadj/{year}/TZA/tza_pd_{year}_1km_UNadj.tif"
        _download_file(url)


def _download_file(url):
    a = urlparse(url)
    f = os.path.basename(a.path)

    if os.path.isfile(f"./input/data/worldpop_pd/{f}"):
        logger.debug("Skipping b/c already downloaded %s", url)
        return

    try:
        subprocess.check_output(['wget', url, "-P", "./input/data/worldpop_pd"])
    except Exception as e:
        logger.warning("Could not download file: %s, %s", url, e)
