import os
import sys, inspect
import datetime as dt
from pathlib import Path
import importlib
import pkgutil

import logging

import click
import pandas as pd
import geopandas
from meteostat import Stations, Daily

import esida.statcompiler as stc
from dbconf import get_engine
import log

from parameters import *

logger = log.setup_custom_logger('root')

@click.group()
def cli():
    pass

@cli.command()
def init():
    """ Init database, by creating database and importing district/region shapes. """

    # regions first, so foreign-keys exist
    regions_gdf = geopandas.read_file('./input/shapes/Districts_Shapefiles_2019/Regions Based on Districts.shp')
    regions_gdf = regions_gdf.rename(columns={
        "Region_Nam": "name",
        "Region_Cod": "region_code",
    })
    regions_gdf['type'] = 'region'
    regions_gdf = regions_gdf.sort_values(by=['region_code'])
    regions_gdf.to_postgis('shape', get_engine(), if_exists='append')

    imported_regions_gdf = geopandas.GeoDataFrame.from_postgis("SELECT * FROM shape WHERE type= 'region'", get_engine(), geom_col='geometry')

    def find_pk_if_region(name):
        for i, row in imported_regions_gdf.iterrows():
            if (row['name'] == name):
                return row['id']
        raise ValueError(f"No parent region id found for region ({name})")

    districts_gdf = geopandas.read_file('./input/shapes/Districts_Shapefiles_2019/Districts and TC as 2020 FIXED.shp')
    districts_gdf = districts_gdf.rename(columns={
        "NewDist20":  "name",
        "Region_Nam": "region_name",
        "Region_Cod": "region_code",
        "District_C": "district_c"
    })
    districts_gdf['type'] = 'district'
    districts_gdf['parent_id'] = districts_gdf['region_name'].apply(find_pk_if_region)
    districts_gdf = districts_gdf.sort_values(by=['region_code', 'district_c'])
    districts_gdf.to_postgis('shape', get_engine(), if_exists='append')

    # calculate district area
    # Date are in ESPG:4326 (deg based), so for ST_Area() to produce m2
    # we need to convert to a meters based system. With utmzone() we identify
    # the resp. used UTM Zone that is m based.
    engine = get_engine()
    with engine.connect() as con:
        con.execute('UPDATE shape SET area_sqm = \
          ST_Area(ST_Transform(geometry, utmzone(ST_Centroid(geometry))))')


@cli.command("list")
def list_parameters():
    """ Print all available parameters. """
    parameters  = [name for _, name, _ in pkgutil.iter_modules(['parameters'])]

    for parameter in parameters:
        print(parameter)

@cli.command()
@click.argument('parameter')
@click.argument('action')
def param(parameter, action):
    params  = [name for _, name, _ in pkgutil.iter_modules(['parameters'])]

    if parameter not in params:
        click.echo(click.style('Unknown parameter',  fg='red'), err=True)
        return

    pmodule = importlib.import_module(f'parameters.{parameter}')
    pclass  = getattr(pmodule, parameter)()
    result = getattr(pclass, action)()



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
