"""
Tanzania Health Facility Register


"""

import logging
import subprocess
import rasterio
import re
import os
import glob
import datetime as dt
import numpy as np
import pandas as pd
import geopandas
from urllib.parse import urlparse

from dbconf import get_engine

parameter_id = 'tza_hfr'
logger = logging.getLogger('root')
districts_gdf = None
stats = {
    'no_date': 0,
    'unix_0': 0,
    'malformed': 0,
    'future': 0,
    'valid': 0
}

def transform():
    global districts_gdf

    # latest download of tza hfr
    list_of_files = glob.glob('./input/data/tza_hfr/*.xls')
    print(list_of_files)
    latest_file = max(list_of_files, key=os.path.getctime)

    # the xls file is actually just a HTML table
    # read_html() always returns a list, even if it's only one table in HTML
    df = pd.read_html(latest_file,
                 header=1, na_values=['Not Set', 'NIL', 'NOT documented', 'not documented'])[0]

    # clean up coordinates
    df['Latitude'] = df.apply(clean_lat, axis=1)
    df['Longitude'] = df.apply(cleat_lng, axis=1)
    df = df.apply(check_for_coord_pair, axis=1)

    # clean up opening date
    df['Date Opened'] = df.apply(parse_date, axis=1)

    # map entries to regions and districts by coordinates
    # text based regions might be reporting authorities and not geographic
    districts_gdf = geopandas.read_postgis("SELECT * FROM district",
                        geom_col='geometry', con=get_engine())

    gdf = geopandas.GeoDataFrame(
        df, geometry=geopandas.points_from_xy(df.Longitude, df.Latitude, crs="EPSG:4326"))

    gdf2 = gdf.apply(get_district_id_by_coord, axis=1)
    gdf['region_id'] = gdf2['region_id_by_coord']
    gdf['district_id'] = gdf2['district_id_by_coord']

    # write all to database that have coordindates inside tanzania
    final = gdf[gdf['region_id'].notna() & gdf['district_id'].notna()]
    final.to_postgis('tza_hfr_healthfacilities', con=get_engine(), if_exists='replace')

def load():
    global districts_gdf

    df = geopandas.read_postgis("SELECT * FROM tza_hfr_healthfacilities",
                        geom_col='geometry', con=get_engine())

    district_ids = sorted(list(df['district_id'].unique()))

    # This mapps different TZA HFR types to one single category we are
    # interrested in
    types = {
        'dispensary': [
            'Dispensary'
        ],
        'health_center': [
            'Health Center'
        ],
        'clinic': [
            'PolyClinic',
            'Optometry Clinic',
            'Medical Clinic'
        ],
        'hospital': [
            'Hospital at District Level',
            'District Hospital',
            'Regional Referral Hospital',
            'Hospital at Regional Level',
            'Hospital at Zonal Level',
            'National Super Specialized Hospital',
            'Zonal Referral Hospital',
            'National Hospital',
        ],
        'health_lab': [
            'Level IA2 (Dispensary Laboratory)',
            'Level III Single purpose Health Laboratory',
            'Level III Multipurpose Health Laboratory',
            'Level IA1 (Health Center Laboratory)',
            'Level IIA2 (District Laboratory)',
        ],
    }

    everything = [] # data for ALL districts

    for district_id in district_ids:
        hf_in_district_df = df[df['district_id'] == district_id].reset_index()
        dfs = [] # total + different type categories for this district

        # total number of healthfacilities
        dfs.append(count_hf_per_year(hf_in_district_df, district_id))

        # count facility per type according to the mapping above
        for type_key, type_names in types.items():
            hf_in_district_of_type_df = hf_in_district_df[hf_in_district_df['Facility Type'].isin(type_names)]
            tmpfx = count_hf_per_year(hf_in_district_of_type_df, district_id)
            tmpfx[type_key] = tmpfx['total']
            dfs.append(tmpfx[['year', type_key]])

        # merge df's on year colum
        results = dfs[0]
        for i in range(1, len(dfs)):
            results = results.merge(dfs[i], how='outer', on='year')

        # fill resulting NaN values
        for type_key, _ in types.items():
            # ffill -> forward fill use all following NaNs and fill them with last known value
            # this will not catch a starting NaN, use backfill for them. This is okay.
            # since this will fill all previous year with ne coun of non openening dates
            # for all remaining NaN values no facillities of that type are in
            # the district, set them to 0.
            results[type_key] = results[type_key].fillna(method='ffill').fillna(method='backfill').fillna(0)

        everything.append(results)

    everything = pd.concat(everything, ignore_index=True).reset_index(drop=True)
    everything.to_sql('tza_hfr_count', con=get_engine(), if_exists='replace')


def count_hf_per_year(hf_in_district_df, district_id):
    # amount w/o date
    without_opening_date = len(hf_in_district_df[hf_in_district_df['Date Opened'].isnull()])

    # only with date
    with_date_df = hf_in_district_df[hf_in_district_df['Date Opened'].notna()]
    with_date_df['year'] = with_date_df['Date Opened'].apply(lambda x: x.year)

    all_per_year_df = with_date_df.groupby('year').size().reset_index(name='count')
    all_per_year_df.index = pd.to_datetime(all_per_year_df['year'], format='%Y')

    all_per_year_df['total'] = all_per_year_df['count'].cumsum()
    all_per_year_df['total'] += without_opening_date

    all_per_year_df['district_id'] = district_id

    # reduce grouped index with duplicate column names
    all_per_year_df.index.names = ['date']

    return all_per_year_df


def consume(file):
    x = re.search(r'[0-9]+', os.path.basename(file))
    year = int(x[0])

    dataset = rasterio.open(file)
    band1 = dataset.read(1, masked=True)

    return {'value': np.nanmean(band1), 'year': year}

def to_sql(rows, engine):
    df = pd.DataFrame(rows)
    df.to_sql(parameter_id, engine)


def download(shape_id, engine):
    sql = "SELECT year, \
    total as tza_hfr_total, \
    dispensary as tza_hfr_dispensary, \
    health_center as tza_hfr_health_center, \
    clinic as hfr_health_clinic, \
    hospital as tza_hfr_hospital, \
    health_lab as tza_hfr_health_lab \
    FROM tza_hfr_count WHERE district_id = {}".format(
        shape_id
    )

    df = pd.read_sql_query(sql, con=engine)

    return df


def completeness_start():
    return 2010

def completeness_end():
    return 2020

def extract():
    url = 'https://hfrportal.moh.go.tz/index.php?r=facilities/exportToExcel&url=http%3A%2F%2F41.59.227.72%2Findex.php%2Fapi%2Fhealth-facility%2Ffacility-list%3Fsearch_query%3Doperating%26search_value%3Dall&report_title=All_Operating_Health_Facilities_in_Tanzania'
    _download_file(url)

def _download_file(url):
    a = urlparse(url)
    f = os.path.basename(a.path)

    if os.path.isfile(f"./input/data/tza_hfr/{f}"):
        logger.debug("Skipping b/c already downloaded %s", url)
        return

    try:
        subprocess.check_output(['wget', url, "-P", "./input/data/tza_hfr"])
    except Exception as e:
        logger.warning("Could not download file: %s, %s", url, e)



def clean_lat_lng(row, key):
    coord = row[key]

    # skip NaN
    if coord != coord:
        return None

    coord_str = str(coord).replace(' ', '')

    if False and coord_str[1] in ['.']:
        if coord_str[0] == 'S':
            return abs(float(coord_str[2:])) * -1
        elif coord_str[0] == 'E':
            return float(coord_str[2:])

    if False and coord_str[0] in ['S', 'E']:
        return float(coord_str[1:])

    try:
        c = float(coord)

        if (key == 'Latitude'):
            if (c > 90 or c < -90):
                logger.warning(f"Latitude out of range ({coord}) for id={row['ID']}")
                return None
        elif (key == 'Longitude'):
            if (c > 180 or c < -180):
                logger.warning(f"Longitude out of range ({coord}) for id={row['ID']}")
                return None
        return c
    except Exception as error:
        logger.warning(f"Malformed {key} ({coord}) for id={row['ID']}")
        return None

def clean_lat(row):
    return clean_lat_lng(row, 'Latitude')

def cleat_lng(row):
    return clean_lat_lng(row, 'Longitude')

def check_for_coord_pair(row):
    """ Make sure lat/lng are both set. """
    no_lat = False
    no_lng = False
    missing= ""
    if row['Latitude'] != row['Latitude']:
        missing += 'Latitude '
        no_lat = True

    if row['Longitude'] != row['Longitude']:
        missing += 'Longitude '
        no_lng = True

    if no_lat ^ no_lng:
        logging.warning(f"Missing one coordinate: {missing}for id={row['ID']}")
        row['Latitude'] = None
        row['Longitude'] = None

    return row

def parse_date(row):
    date = row['Date Opened']

    # Skip NaN
    if date != date:
        stats['no_date'] += 1
        return pd.NaT

    # Skip timestamp=0
    if date == '1970-01-01':
        # is quite a lot...
        #logging.warning(f"Date is set to Unixtimstamp=0 for id={row['ID']}")
        stats['unix_0'] += 1
        return pd.NaT

    try:
        dtime = pd.to_datetime(date, format='%Y-%m-%d')

        if dtime > dt.datetime.now():
            stats['future'] += 1
            logger.warning(f"Date is in the future ({date}) for with state {row['Operating Status']} id={row['ID']}")
        else:
            stats['valid'] += 1

        return dtime
    except ValueError as e:
        logger.warning(f"Malformed date string ({date}) for id={row['ID']}")
        stats['malformed'] += 1
        return pd.NaT

def get_district_id_by_coord(row):
    point = row['geometry']

    row['region_id_by_coord'] = None
    row['district_id_by_coord'] = None

    # ps.isna() etc WON'T catch an empty geometry from geopands!
    if point.is_empty:
        return row

    match_district = districts_gdf[districts_gdf['geometry'].contains(point)].reset_index()

    if len(match_district) != 1:
        logger.warning(f"Could not match coordinate to district for id={row['ID']}")
        return row

    row['region_id_by_coord'] = match_district.at[0, 'region_id']
    row['district_id_by_coord'] = match_district.at[0, 'id']

    return row
