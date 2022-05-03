"""
Malaria incidence found by Juliane.
"""

import re
import os
import rasterio
import numpy as np
import pandas as pd

from dbconf import get_engine


parameter_id = 'malariaatlas_incidence'

def consume(file, district_id=None):
    x = re.search(r'[0-9]{4}', os.path.basename(file))
    year = int(x[0])

    dataset = rasterio.open(file)
    band1 = dataset.read(1, masked=True)

    return {parameter_id: np.nanmean(band1), 'year': year}

def to_sql(rows, engine):
    df = pd.DataFrame(rows)
    df.to_sql(parameter_id, engine, if_exists='replace')

def is_loaded() -> bool:
    engine = get_engine()
    with engine.connect() as con:
        r = con.execute("select exists(select * from information_schema.tables where table_name=%s)", (parameter_id,))
        return r.first()[0]
    return False

def download(shape_id, engine) -> pd.DataFrame():

    if not is_loaded():
        return pd.DataFrame()

    sql = "SELECT year, {} FROM {} WHERE district_id = {}".format(
        parameter_id, parameter_id,
        shape_id
    )

    df = pd.read_sql_query(sql, con=engine)

    return df
