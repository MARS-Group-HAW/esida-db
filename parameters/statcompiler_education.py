"""

[Statcompiler dashboard](https://www.statcompiler.com/en/#cc=TZ&ucc=&ic=ED_EDUC_W_MYR,ED_EDUC_M_MYR&scl=10000,451001,451002,451004,451005,451006,451007,451008,451011,451012,451013,451014,451015,451016,451017,451018,451019,451020,451021,451022,451023,451024,451025,451026,451027,451028,451029,451030,451003,451023,451030,451040,451041,451042,451043,451044,451045,451009,451010,451011,451014,451018,451026,451001,451005,451022,451030,451031,451032,451033,451034,451035,451043,451065,451072,451073,451081,451082,451084,451086,451087,451088,451089,451090,451091,451092,1000&dt=4&pt=2&ss=2&sy=&levelRank=1&si=ED_EDUC_M_MYR&sbv=)


"""

import os
import pandas as pd

indicators = ['ED_EDUC_W_MYR', 'ED_EDUC_M_MYR']
parameter_id = 'statcompiler_education'

def consume(file):
    pass

def to_sql(df, engine):
    df.to_sql(parameter_id, engine)

def compute(df):
    df['sum'] = df[indicators].sum(axis=1, min_count=1)
    df['avg'] = df[indicators].mean(axis=1)

    return df


def download(shape_id, engine):
    sql = "SELECT year, avg as {} FROM {} WHERE region_id = (SELECT region_id FROM district WHERE id = {})".format(
        parameter_id, parameter_id,
        shape_id
    )

    df = pd.read_sql_query(sql, con=engine)

    return df
