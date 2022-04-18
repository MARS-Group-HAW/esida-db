import os
import datetime as dt
from pathlib import Path
import importlib
import pkgutil

import click
import pandas as pd
import geopandas
from meteostat import Stations, Daily

import esida.statcompiler as stc
from dbconf import get_engine


@click.group()
def cli():
    pass

@cli.command()
def init():
    """ Init database, by creating database and importing district/region shapes. """

    # regions first, so foreign-keys exist
    regions_gdf = geopandas.read_file('./input/shapes/Districts_Shapefiles_2019/Regions based on Distrcits.shp')
    regions_gdf = regions_gdf.rename(columns={
        "Region_Nam": "name",
        "Region_Cod": "region_id",
    })
    regions_gdf.to_postgis('region', get_engine(), if_exists='append')


    districts_gdf = geopandas.read_file('./input/shapes/Districts_Shapefiles_2019/Districts and TC as 2020 FIXED.shp')
    districts_gdf = districts_gdf.rename(columns={
        "NewDist20":  "name",
        "Region_Nam": "region_name",
        "Region_Cod": "region_id",
        "District_C": "district_c"
    })

    districts_gdf.to_postgis('district', get_engine(), if_exists='append')

@cli.command()
@click.option('-p', '--parameter', default=None, type=str)
def statcompiler(parameter):
    """ Import statcompiler sources. """

    engine  = get_engine()
    outputs = sorted(os.listdir("./output/"))

    params  = ['statcompiler_education']
    if parameter is not None:
        params = [parameter]

    regions_df = pd.read_sql_query('SELECT region_id, name FROM region ORDER by name', con=engine)

    for p in params:
        pm = importlib.import_module(f'parameters.{p}')

        df = stc.fetch_from_stat_compiler(pm.indicators)

        # safe raw data
        output_dir = Path(f'input/data/{p}/')
        output_file = '{}_data_{}.csv'.format(dt.datetime.today().strftime('%Y-%m-%d_%H-%M-%S'), p)
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


@cli.command()
def meteostat():
    """ Fetch meteostat stations and data. """

    # Database access
    engine  = get_engine()

    # fetch Meteostat weather stations for TZ
    stations = Stations()
    stations = stations.region('TZ')
    print('Stations in Tanzania:', stations.count())

    df = stations.fetch()

    # Meteostat ID is not always numerical. Safe the internal Meteostat ID
    # but add an numerical index for smooth PostGis access
    df['meteostat_id'] = df.index
    df.insert(0, 'meteostat_id', df.pop('meteostat_id')) # move meteostat ID to second column (directly ≤after index)

    df['id'] = range(1, len(df)+1)
    df.insert(0, 'id', df.pop('id'))

    gdf = geopandas.GeoDataFrame(
        df, geometry=geopandas.points_from_xy(df.longitude, df.latitude))


    gdf.to_postgis("meteostat_stations", engine, if_exists='replace')


    # loop over all stations and collect daily values
    start = dt.datetime(2000, 1, 1)
    end = dt.datetime(2021, 3, 31)

    dfs = []

    for i, row in gdf.iterrows():
        print("Fetching {} ({})".format(row['name'], row['meteostat_id']))
        data = Daily(row['meteostat_id'], start, end)
        data = data.fetch()

        print("Found {} rows".format(len(data)))
        data['meteostat_station_id'] = row['id']
        dfs.append(data)

    merged_df = pd.concat(dfs)
    merged_df.to_sql("meteostat_data", engine, if_exists='replace')



if __name__ == '__main__':
    cli()
