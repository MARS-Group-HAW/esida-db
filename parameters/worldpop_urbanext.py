"""
Demographic Urban Settlement Extent optional

| Information     | Comment                                                      |
| --------------- | ------------------------------------------------------------ |
| Source          | [Worldpop]( https://www.worldpop.org/geodata/summary?id=17285) |
| Format          | `tiff`, 100 × 100 m                                          |
| Operation       | binary (0=not urban, 1=urban)                                |
| Temporal extent | 2010, 2020                                                   |

**Todo**:

- are `bsgme` and `bgsmi` the same parameter or different?

"""

import logging
import subprocess
import rasterio
import re
import os
from urllib.parse import urlparse

import numpy as np
import pandas as pd

parameter_id = 'worldpop_urbanext'
logger = logging.getLogger('root')


def consume(file, district_id=None):
    x = re.search(r'[0-9]{4}', os.path.basename(file))
    year = int(x[0])

    dataset = rasterio.open(file)
    band1 = dataset.read(1, masked=True)

    total_cells = band1.count()
    set_cells = np.count_nonzero(band1==1)

    return {parameter_id: set_cells / total_cells, 'year': year}

def to_sql(rows, engine):
    df = pd.DataFrame(rows)
    df.to_sql(parameter_id, engine)

def download(shape_id, engine):
    sql = "SELECT year, {} FROM {} WHERE district_id = {}".format(
        parameter_id, parameter_id,
        shape_id
    )

    df = pd.read_sql_query(sql, con=engine)

    return df

def extract():
    # bsgmi 2001 - 2013
    for year in range(2010, 2013+1):
        url = f"https://data.worldpop.org/GIS/Global_Settlement_Growth/Individual_countries/TZA/v0a/tza_bsgmi_v0a_100m_{year}.tif"
        _download_file(url)

    # bsgme 2015 - 2020
    for year in range(2015, 2020+1):
        url = f"https://data.worldpop.org/GIS/Global_Settlement_Growth/Individual_countries/TZA/v0a/tza_bsgme_v0a_100m_{year}.tif"
        _download_file(url)


def _download_file(url):
    a = urlparse(url)
    f = os.path.basename(a.path)

    if os.path.isfile(f"./input/data/worldpop_urbanext/{f}"):
        logger.debug("Skipping b/c already downloaded %s", url)
        return

    try:
        subprocess.check_output(['wget', url, "-P", "./input/data/worldpop_urbanext"])
    except Exception as e:
        logger.warning("Could not download file: %s, %s", url, e)
