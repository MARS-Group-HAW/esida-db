import os
import json
import pkgutil
import importlib
import datetime as dt
from pathlib import Path
from distutils.dir_util import copy_tree



import click
import shapely
import shapely.wkt
import geopandas
import pandas as pd
import sqlalchemy

import log
from dbconf import get_engine, connect, close
from parameters import *
from esida.tiff_parameter import TiffParameter


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
    regions_gdf[['name', 'geometry', 'type']].to_postgis('shape', connect(), if_exists='append')

    imported_regions_gdf = geopandas.GeoDataFrame.from_postgis("SELECT * FROM shape WHERE type= 'region'", connect(), geom_col='geometry')

    def find_pk_if_region(name):
        for _, row in imported_regions_gdf.iterrows():
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
    districts_gdf[['name', 'parent_id', 'type', 'geometry']].to_postgis('shape', connect(), if_exists='append')

    # calculate district area
    # Date are in ESPG:4326 (deg based), so for ST_Area() to produce m2
    # we need to convert to a meters based system. With utmzone() we identify
    # the resp. used UTM Zone that is m based.
    con = connect()
    con.execute('UPDATE shape SET area_sqm = \
        ST_Area(ST_Transform(geometry, utmzone(ST_Centroid(geometry))))')

@cli.command("load-shapes")
@click.argument('file', type=click.Path(exists=True))
def load_shapes(file):
    gdf = geopandas.read_file(file)
    required_cols = ['id', 'name', 'type', 'parent_id', 'geometry']

    # make sure our required columns exist
    for col in required_cols:
        if col not in gdf.columns:
            raise click.UsageError(f"{col} column is required")

    # In Geopandas/Pandas there is no None/Null value for Integers. So our
    # parent_id column with the int reference is of type float (b/c upper most
    # shapes have no parent_id).
    # SQLAlchemy / Geopandas to_postgis() can't handle a float in enforcing the
    # foreign key to the parent row.
    # ...so we need to split our input data in parent only rows and child rows
    # and import them separately.
    gdf_no_parent = gdf[gdf['parent_id'].isna()]
    gdf_no_parent[['id', 'name', 'type', 'geometry']].to_postgis('shape', connect(), if_exists='append')

    gdf_with_parent = gdf[gdf['parent_id'].notna()]
    gdf_with_parent['parent_id'] = gdf_with_parent['parent_id'].astype('int') # no isna() rows left => cast to int, so SQLAlchemy can write to PostGis
    gdf_with_parent[required_cols].to_postgis('shape', connect(), if_exists='append')

    # calculate shape area
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
    """ Execute action on parameter, like load, transform or extract. """

    params  = [name for _, name, _ in pkgutil.iter_modules(['parameters'])]

    if parameter not in params:
        click.echo(click.style('Unknown parameter',  fg='red'), err=True)
        return

    pmodule = importlib.import_module(f'parameters.{parameter}')
    pclass  = getattr(pmodule, parameter)()
    result = getattr(pclass, action)()


@cli.command()
@click.argument('parameter', required=False, type=str)
@click.option('--shape_id', required=False, type=int)
def daspatial(parameter, shape_id):
    """ Generate long running spatial quality of applicable parameters. """

    if not parameter:
        params  = [name for _, name, _ in pkgutil.iter_modules(['parameters'])]
    else:
        params = [parameter]
    summary = []

    now = dt.datetime.now()
    out_name = now.strftime("%Y-%m-%d_%H-%M-%S")
    out_name += "_DA_Spatial"
    out_dir = Path("./output") / out_name
    out_dir.mkdir(parents=True, exist_ok=True)


    for p in params:
        pmodule = importlib.import_module(f'parameters.{p}')
        pc  = getattr(pmodule, p)()

        if not isinstance(pc, TiffParameter):
            continue

        result, results = pc.da_spatial(shape_id)

        summary.append({
            'data_layer': p,
            'spatial_coverage': result,
        })

        # save summary in each loop iteration to save output early.
        # generation takes long!
        dfx = pd.DataFrame(summary)
        dfx.to_csv(out_dir / 'da_spatial.csv', index=False)

        dfx = pd.DataFrame(results)
        dfx.to_csv(out_dir / f'files_{p}.csv', index=False)


@cli.command()
@click.option('--wkt')
@click.option('--abm', is_flag=True)
def clip(wkt, abm):
    """ Get metrics for the given AOI, provide either a WKT string or file.

    If the abm flag is present only data layers relevant for the ABM are
    exported and a config.json is generated.

    """
    params  = [name for _, name, _ in pkgutil.iter_modules(['parameters'])]

    now = dt.datetime.now()
    out_name = now.strftime("%Y-%m-%d_%H-%M-%S") + "_clip"
    if os.path.exists(wkt):
        out_name += "_"+os.path.basename(wkt)
        with open(wkt, 'r') as file:
            wkt = file.read()

    geometry = shapely.wkt.loads(wkt)
    if geometry.geom_type != 'Polygon':
        click.echo(click.style('Only POLYGON is allowed as input geometry.',  fg='red'), err=True)

    out_dir = Path("./output") / out_name
    out_resources = out_dir / "resources"
    out_resources.mkdir(parents=True, exist_ok=True)
    shape = {
        'geometry': geometry,
        'name': 'text',
        'id': 0,
    }

    for p in params:
        if abm and p not in [
                'worldpop_popc',
                'geofabrik_pois',
                'osm_graph',
                'osm_building',
                'osm_landuse',
                'rcmrd_elev',
                'meteo_tprecit',
                'visualcrossing_weather'
            ]:
            continue

        pmodule = importlib.import_module(f'parameters.{p}')
        pclass  = getattr(pmodule, p)()
        pclass.set_output_path(out_resources)
        pclass.output = 'fs' # save products to file system instead of database
        result = getattr(pclass, 'load')(shapes=[shape], save_output=True)

    # the following prepared the config.json for the MARS ABM
    # so if we don't have the abm flag this is not necessary.
    if not abm:
        return

    # after creating layers
    # calculate amount of needed agents
    dfx = pd.read_csv(out_resources / 'worldpop_popc.csv')
    agent_count = int(dfx['worldpop_popc'].tail(1))

    p = 'cia_worldfactbook'
    pmodule = importlib.import_module(f'parameters.{p}')
    pclass  = getattr(pmodule, p)()
    pclass.set_output_path(out_resources)
    pclass.output = 'fs' # save products to file system instead of database
    result = getattr(pclass, 'load')(shapes=[shape], save_output=True, agent_count=agent_count)

    copy_tree("input/data/MARS", out_dir.as_posix())

    # prepare config.json
    with open('input/data/MARS/config.json') as f:
        d = json.load(f)

        # set date
        start = dt.datetime.now()
        end   = start + dt.timedelta(days=14+1) # +1 so we don't need to run until 23:59:59
        d['globals']['startPoint'] = start.strftime('%Y-%m-%dT00:00:00')
        d['globals']['endPoint']   = end.strftime('%Y-%m-%dT00:00:00')

        # Geometries for temp/prcp CSV spatial join
        geometry_json = shapely.geometry.mapping(geometry)
        for d2 in d['layers']:
            if d2['name'] in ['TemperatureLayer', 'PrecipitationLayer']:
                for d3 in d2['inputs']:
                    if "value" in d3:
                        d3['value']['geometry'] = geometry_json

        # set agent count
        for d2 in d['agents']:
            if d2['name'] == 'Human':
                d2['count'] = agent_count

        with open(out_dir / 'config.json', 'w') as f:
            json.dump(d, f, indent=2)

if __name__ == '__main__':
    cli()

    # make sure potentially open database connections are closed
    close()
