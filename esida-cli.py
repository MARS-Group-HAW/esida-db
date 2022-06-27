import os
import pkgutil
import shapely
import importlib
from pathlib import Path

import click
import geopandas

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
@click.option('--signal', '-s', multiple=True)
def abm(signal):
    pass

@cli.command()
@click.option('--wkt')
def clip(wkt):
    params  = [name for _, name, _ in pkgutil.iter_modules(['parameters'])]

    if os.path.exists(wkt):
        with open(wkt, 'r') as file:
            wkt = file.read()

    shape = {
        'geometry': shapely.wkt.loads(wkt),
        'name': 'text',
        'id': 0,
    }

    for p in params:

        if p != 'worldpop_popc':
            continue

        pmodule = importlib.import_module(f'parameters.{p}')
        pclass  = getattr(pmodule, p)()
        pclass.set_output_path(Path("./test"))
        pclass.output = 'fs' # save products to file system instead of database
        result = getattr(pclass, 'load')(shapes=[shape], save_output=True)

if __name__ == '__main__':
    cli()

    # make sure potentially open database connections are closed
    close()
