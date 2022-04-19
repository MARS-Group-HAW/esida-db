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

parameter_id = 'worldpop_popc'

def consume(file):
    x = re.search(r'[0-9]+', os.path.basename(file))
    year = int(x[0])

    dataset = rasterio.open(file)
    band1 = dataset.read(1, masked=True)

    return {'value': np.nansum(band1), 'year': year}

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

def get():
    for y in range(2010, 2020+1):
        url = f"https://data.worldpop.org/GIS/Population/Global_2000_2020/{y}/TZA/tza_ppp_{y}_UNadj.tif"
        print(subprocess.check_output(['wget', url, "-P", "./input/data/worldpop_popc"]))
