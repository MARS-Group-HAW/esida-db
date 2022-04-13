import os
import pandas as pd
import importlib
import pkgutil
from dbconf import get_engine
import datetime as dt
from pathlib import Path
import app.statcompiler as stc

engine  = get_engine()
outputs = sorted(os.listdir("./output/"))
params  = ['statcompiler_cellphone']

regions_df = pd.read_sql_query('SELECT r.region_cod as region_id, r.region_nam as name FROM regions r ORDER by name', con=engine)

for p in params:
    pm = importlib.import_module('parameters.{}'.format(p))

    df = stc.fetch_from_stat_compiler(pm.indicators)

    # safe raw data
    output_dir = Path('input/data/{}/'.format(p))
    output_file = '{}_data.csv'.format(dt.datetime.today().strftime('%Y-%m-%d_%H-%M-%S'))
    output_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_dir / output_file, index=False)

    # cleanup data
    # remove the generic / zone admin levels and only leave regions
    df['is_region'] = df['CharacteristicLabel'].apply(stc.is_region)
    df = df[df['is_region'] == True]

    df['CharacteristicLabel'] = df['CharacteristicLabel'].apply(stc.normalize_region_name)
    df['CharacteristicLabel'] = df['CharacteristicLabel'].apply(stc.map_region_name_to_tz_stat_names)

    # group
    df = stc.group_per_studyyear_region(df, pm.indicators, regions_df)

    # statcompiler specific data wrangling
    df = pm.compute(df)

    pm.to_sql(df, engine)
