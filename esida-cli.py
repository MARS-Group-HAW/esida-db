import os
import pkgutil
import shapely
import importlib
from pathlib import Path
import datetime as dt

import click
import geopandas
import pandas as pd

from dbconf import get_engine, connect, close
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
    regions_gdf.to_postgis('shape', connect(), if_exists='append')

    imported_regions_gdf = geopandas.GeoDataFrame.from_postgis("SELECT * FROM shape WHERE type= 'region'", connect(), geom_col='geometry')

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
    districts_gdf.to_postgis('shape', connect(), if_exists='append')

    # calculate district area
    # Date are in ESPG:4326 (deg based), so for ST_Area() to produce m2
    # we need to convert to a meters based system. With utmzone() we identify
    # the resp. used UTM Zone that is m based.
    con = connect()
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
def load():
    params  = [name for _, name, _ in pkgutil.iter_modules(['parameters'])]

    action = 'load'
    no_extract = [
        'cia_worldfactbook',
        'geofabrik_pois',
        'osm_building',
        'osm_graph',
        'osm_landuse',
    ]

    for parameter in params:

        if parameter in no_extract:
            continue

        pmodule = importlib.import_module(f'parameters.{parameter}')
        pclass  = getattr(pmodule, parameter)()
        result = getattr(pclass, action)()


@cli.command()
@click.option('--signal', '-s', multiple=True)
def abm(signal):
    pass

@cli.command()
@click.option('--wkt')
@click.option('--abm', is_flag=True)
def clip(wkt, abm):
    params  = [name for _, name, _ in pkgutil.iter_modules(['parameters'])]

    now = dt.datetime.now()
    out_name = now.strftime("%Y-%m-%d_%H-%M-%S")
    if os.path.exists(wkt):
        out_name += "_"+os.path.basename(wkt)
        with open(wkt, 'r') as file:
            wkt = file.read()


    out_dir = Path("./output/") / out_name
    shape = {
        'geometry': shapely.wkt.loads(wkt),
        'name': 'text',
        'id': 0,
    }

    for p in params:

        if abm and p not in ['worldpop_popc', 'geofabrik_pois', 'osm_graph', 'osm_building', 'osm_landuse', 'rcmrd_elev', 'meteo_tprecit']:
            continue

        pmodule = importlib.import_module(f'parameters.{p}')
        pclass  = getattr(pmodule, p)()
        pclass.set_output_path(out_dir)
        pclass.output = 'fs' # save products to file system instead of database
        result = getattr(pclass, 'load')(shapes=[shape], save_output=True)

    # after creating layers
    # calculate amount of needed agents
    dfx = pd.read_csv(out_dir / 'worldpop_popc.csv')
    agent_count = int(dfx['worldpop_popc_sum'].tail(1))


    p = 'cia_worldfactbook'
    pmodule = importlib.import_module(f'parameters.{p}')
    pclass  = getattr(pmodule, p)()
    pclass.set_output_path(out_dir)
    pclass.output = 'fs' # save products to file system instead of database
    result = getattr(pclass, 'load')(shapes=[shape], save_output=True, agent_count=agent_count)

if __name__ == '__main__':
    cli()

    # make sure potentially open database connections are closed
    close()
