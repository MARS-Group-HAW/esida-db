"""
Malaria incidence found by Juliane.
"""

import rasterio
import re
import os
import numpy as np
import pandas as pd

parameter_id = 'malaria'

def consume(file, district_id=None):
    x = re.search(r'[0-9]{4}', os.path.basename(file))
    year = int(x[0])

    dataset = rasterio.open(file)
    band1 = dataset.read(1, masked=True)

    return {'value': np.nanmean(band1), 'year': year}

def to_sql(rows, engine):
    df = pd.DataFrame(rows)
    df.to_sql(parameter_id, engine, if_exists='replace')

def download(shape_id, engine):
    sql = "SELECT year, value as {} FROM {} WHERE district_id = {}".format(
        parameter_id, parameter_id,
        shape_id
    )

    df = pd.read_sql_query(sql, con=engine)

    return df
