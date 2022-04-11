from meteostat import Stations, Daily
import geopandas
import pandas as pd
from dbconf import get_engine
import datetime as dt


stations = Stations()
stations = stations.region('TZ')

print('Stations in Tanzania:', stations.count())


df = stations.fetch()


gdf = geopandas.GeoDataFrame(
    df, geometry=geopandas.points_from_xy(df.longitude, df.latitude))

engine  = get_engine()

gdf['id'] = gdf.index
gdf.to_postgis("meteostat_stations", engine, if_exists='replace')

exit()

start = dt.datetime(2000, 1, 1)
end = dt.datetime(2020, 12, 31)

dfs = []

for i, row in gdf.iterrows():
    print("Fetching {} ({})".format(row['name'], i))
    data = Daily(i, start, end)
    data = data.fetch()

    data['meteostat_station_id'] = i
    dfs.append(data)

merged_df = pd.concat(dfs)
merged_df.to_sql("meteostat_data", engine, if_exists='replace')
