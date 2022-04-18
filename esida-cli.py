import click
import pandas as pd
import geopandas

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



if __name__ == '__main__':
    cli()
