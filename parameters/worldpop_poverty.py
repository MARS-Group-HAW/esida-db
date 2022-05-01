"""
Demographic	Population counts


- tiff 100 x 100 m
- sum total number
- Annualy (2010-2020)
- [Worldpop](https://www.worldpop.org/geodata/listing?id=69)

"""
import subprocess

import rasterio
import re
import os
import numpy as np
import pandas as pd

parameter_id = 'worldpop_poverty'

data = {}

def consume(file, district_id=None):
    x = re.search(r'^tza([0-9]{2})([a-z0-9-]+)\.', os.path.basename(file))
    year = 2000 + int(x[1])

    dataset = rasterio.open(file)
    band1 = dataset.read(1, masked=True)

    if (district_id not in data):
        data[district_id] = {'year': year }

    data[district_id][x[2].replace('-', '')] = np.nanmean(band1)

    return {} # return empty dict to prevent error in calling script

def to_sql(rows, engine):
    df = pd.DataFrame.from_dict(data, orient='index')
    df['district_id'] = df.index
    df.to_sql(parameter_id, engine, if_exists="replace")

def download(shape_id, engine):
    sql = "SELECT year, povcons125 as {key}_povcons125, \
        povcons125uncert as {key}_povcons125uncert, \
        povcons200 as {key}_povcons200, \
        povcons200uncert as {key}_povcons200uncert, \
        povmpiuncert as {key}_povmpiuncert, \
        povmpi as {key}_povmpi FROM {key} WHERE district_id = {id}".format(
        key=parameter_id,
        id=shape_id
    )

    df = pd.read_sql_query(sql, con=engine)

    return df

def extract():
    """ Download needed files, since this is 7z archive and we don't want
    to clutter out container with many tools, and die actual files are
    not that large, we also have those files in the git repository"""
    pass
    #subprocess.check_output(['wget', 'https://data.worldpop.org/GIS/Development_and_health_indicators/Individual_countries/Poverty/TZA/80.7z', "-P", "./input/data/worldpop_poverty"])
