from meteostat import Stations, Daily
import geopandas
import pandas as pd
from dbconf import get_engine
import datetime as dt

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
