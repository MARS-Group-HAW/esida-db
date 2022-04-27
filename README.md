# ESIDA DB GIS Data


## Development

Build Docker container:

    $ docker build -t esida-db .

Run docker container locally:

    $ docker run -e -p 8080:80 esida-db

The database now runs at http://localhost:8080/ (but with no database)


## Setup

Install postgis with

    $ docker-compose up -d

Import shape files with:

    $ shp2pgsql "./input/shapes/Districts_Shapefiles_2019/Districts and TC as 2020 FIXED.shp" districts | psql -h localhost -d esida -U esida

    $ shp2pgsql "./input/shapes/Districts_Shapefiles_2019/Regions based on Distrcits.shp" regions | psql -h localhost -d esida -U esida



Start Flask web-interface:

    export FLASK_ENV=development
    flask run


https://geotiff.io/


----

Tools:

- Python [rasterio](https://rasterio.readthedocs.io/en/latest/api/index.html) - >1k GitHub Stars, read GeoTiff data in python and manipulate the cell values
- Python [rasterstats](https://pythonhosted.org/rasterstats/), very small library to generate stats about geometries in GeoTiff files, based on rasterio, should probably not be used.
- GDAL [gdalwarp](https://gdal.org/programs/gdalwarp.html) clipping of GeoTiff based on .shp file

Relevant posts:

- SO [Clipping GeoTIFF with shapefile?](https://gis.stackexchange.com/questions/297088/clipping-geotiff-with-shapefile) QGIS manual for clipping as well as hint to `gdalwarp` CLI tool (that is used by QGIS)
- SO [Clipping raster with vector boundaries using QGIS](https://gis.stackexchange.com/questions/10117/clipping-raster-with-vector-boundaries-using-qgis) QGIS and Python example, as well as `gdalwarp` recommendation



## To-dos

- Some districts are broken in the Shapefile (self intersecting polygons), better data source? Cleanup required
- Shapefile is slightly shifted after converting to WGS84=






## Splitting w/o database

Splitting Tanzania district Shapefile into one Shape file per district.

- Open layer in QGIS
- Convert layer to WGS84 (??? Validate!)
- Vector > Data management tools > Split vector layers
    - Rerun icon
    - output file format to `.shp`
    - output directory needs an additional slash
    - produces nested output, flatten with zsh: `% mv ./*/**/*(.D) .`
- Run `./clip.sh`
- Results in output for further analyzing with Python (?)


## PostGIS


Include the following PostGIS realted CLI tools in the Docker image: https://github.com/postgis/docker-postgis/tree/master/examples/image-with-postgis-clis


Import shapes of districts into PostGIS:

    shp2pgsql -s 4210:4326 data/GIS_Maps/Districts.shp dsistricts | psql -h localhost -d esida -U esida


- PostGIs raster type: https://postgis.net/docs/using_raster_dataman.html
- https://subscription.packtpub.com/book/big_data_and_business_intelligence/9781784391645/1/ch01lvl1sec7/loading-rasters-using-raster2pgsql
- [Optimum Raster tile size](https://gis.stackexchange.com/questions/300887/optimum-raster-tile-size) - unclear "in the range of 32x32 and 100x100 would be optimal", why?
- https://www.postgis.net/2014/09/26/tip_count_of_pixel_values/
-

Import GeoTiff into PostGIS (different approaches):

    # create intermediate sql file
    raster2pgsql -d -t 256x256 data/worldpop_pop/tza_ppp_2020_UNadj.tiff > tmp.sql

    #
    raster2pgsql -d -t 256x256 data/worldpop_pop/tza_ppp_2020_UNadj.tiff | psql -h localhost -d esida -U esida

    # smaller tile size, and create indizes
    # took around 3,4 hours (MacBook Pro M1)
    raster2pgsql -d -s 4326 -C -l 2,4 -I -F -t 50x50 data/worldpop_pop/tza_ppp_2020_UNadj.tiff | psql -h localhost -U esida -d esida

Subsequent SQL queries are not fast <1m, but not sure how the query is best formulated:

- `ST_Intersects()` -> which tiles are requried (50x50 from above)
- `ST_Clip()` -> select only points/values inside shape file of district
- `ST_PixelAsPoints()` select value and POINT(…) to allow usage in pandas i.e. (export sql query result as CSV)

```sql
SELECT
	(ST_PixelAsPoints(ST_Clip(rast, (SELECT geom FROM dsistricts WHERE gid = 97), 1))).*
FROM
	tza_ppp_2020_unadj

WHERE
	 ST_Intersects(rast, (SELECT geom FROM dsistricts WHERE gid = 97));
```

