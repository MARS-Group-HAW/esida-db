# ESIDA Data Hub

Python based framework for downloading and calculating spatio-temporal data to different areas of interest, like administrative levels of a country, or other shapes.

It aims to be a decision system for epidemiology and can provide an overview with socioecological per administrative level. It is developed in the context of the [ESIDA project](https://www.haw-hamburg.de/en/research/research-projects/project/project/show/esida/) and focused on Tanzania. But this framework aims to be agnostic to its data, so you can use it for different areas and data! See the section below about [setting up a different region](#use-your-own-geographic-region-and-data).


## Usage

### Access data

Two means of data access are provided. For all loaded shapes the available parameter data associated with it can be downloaded as CSV file. For each parameter a download containing all shapes for this parameter is provided as well. Those downloads can be accessed via the web frontend.

Also a simple REST like API is provided to query the shape and parameter data programmatically. See the Jupyter notebook `notebooks/ESIDA DB Demo.ipynb` for further explanation and usage examples of the API.

Data quality metrics can be extracted as well with the API, for this see the notebook `notebooks/ESIDA DB Data Quality.ipynb`. In this case it is recommended to use the system locally since the queries for spatial data quality can be quite long-running, and it might not be possible to query them from a remote host.

### Extract data for arbitrary area

After ingesting data you can calculate the data for an arbitrary region inside the area of the imported data.

    $ python ./eisda-cli.py clip --wkt <path to WKT Polygon> --abm

This will generate a simulation blueprint with the required input data.

The `--abm` flag can be used to only export the relevant data needed for the MARS agent based model.

### Use your own geographic region and data

The Data Hub can be used with any geographic areas, the areas can be organized hierarchically (i.e. administrative levels of a country). But the data need to be prepared in the format of the Data Hub before they can be used. See the provided Jupyter Notebook on how to prepare a shape file for the Data Hub, this example uses Shape files from [GADM](https://gadm.org/download_country.html) which provides shape data for many countries of the world. After preparing the data you can import them with `$ python esida-cli.py load-shapes <path to shp file>`. You also need to define the `DATAHUB_SHAPE_TYPES` constant in the `.env` file with a space separated list of the categories/types of your shapes. For Germany this might look like `DATAHUB_SHAPE_TYPES="country state district"`.

After preparing the area of interest for your Data Hub you can customize the used data. For this look at the different examples inside the `parameters/` folder. For two different data sources the alterations are explained in the following:

#### Meteostat

[Meteostat](https://meteostat.net/) aggregates different weather stations around the world. To get precipitation/temperature data for your region, open the different `parameters/meteo_*.py` classes, i.e. `meteo_tprecit` for precipitation. This parameter utilizes the ability to derive a parameter from another parent parameter class ([DRY principle](https://en.wikipedia.org/wiki/Don%27t_repeat_yourself)). In this case it's the `MeteostatParameter` class which combines different functions for accessing the Meteostat data. You can find the base class in `esida/meteostat_parameter.py`.

To use your region we need to change two things:

1. In the first lines of the `extract()` function you can change the region code to your country: `stations = stations.region('__cc__')`
2. The volume of available weather stations varies around the globe, change the data range for that you want to download data to something smaller like a month. A few lines below the first alteration, change the `start` and `end` variables.

Now you can import the data to the Data Hub with:

    $ python ./esida-cli.py param meteo_tprecit extract # downloading weather station and data
    $ python ./esida-cli.py param meteo_tprecit load    # calculating data for your imported shapes

#### Copernicus Landusage

[Copernicus](https://lcviewer.vito.be/) provides classification of different land types, i.e. forest, cropland, built-up. To use the data in the Data Hub you need to open the base class for the Copernicus Land-usage Data Layer at `esida/copernicus_parameter.py`. Inside the `extract()` function you see the `tiles` variable in which you can define download links for the tiles you need for your region. The different tiles and what land they cover you can find [here](https://lcviewer.vito.be/download).

After adapting the download links to your need, you can download an process the data with:

    $ python ./esida-cli.py param copernicus_crop extract # downloading weather station and data
    $ python ./esida-cli.py param copernicus_crop load    # calculating data for your imported shapes

All other `copernicus_*` parameters only need to execute the `load` command since the input data is shared between the layers.

## Installation

### Local setup (Docker)

Clone the repository.

Create the `.env` file and make sure it's correct populated:

    $ cp .env.example .env

For the local data to the needed destination (this is to pre-fill the persistent data mount needed in Kubernetes):

    $ rsync -a input/data.local/ input/data/

If you need to run the MARS ABM, store the zip files of the boxes inside `./input/dat/MARS/`.

Build and start the containers:

    $ docker-compose up -d

After this you can start/stop the containers with

    $ docker-compose start|stop

The Data Hub is available at [http://localhost/](http://localhost/) - though it is empty at the moment
and not everything works. To set it up follow these steps:

Enter the Docker container (Docker GUI CLI or `$ docker-compose exec esida bash`) and run the following commands.
Those are only required to be run after the first setup.

    $ flask create-db          # setup required database columns
    $ python esida-cli.py init # import Tanzania region/district shape files into db |OR|
    $ python esida-cli.py load <path-to-shape-file> # import hierarchical prepared regions (see above)

After that you can load the different parameters by key into the database:

    $ python ./esida-cli.py param <key> extract # downloads files from source
    $ python ./esida-cli.py param <key> load    # processes source and saves to datab

For example to load Meteostat weather data:

    $ python ./esida-cli.py param meteo_tprecit extract
    $ python ./esida-cli.py param meteo_tprecit load

For available parameters see the listing at [http://localhost/parameter](http://localhost/parameter). After loading, you can use the download function for each shape or use the API to get the data (see Jupyter Notebook in folder `./notebooks/ESIDA DB Demo.ipynb`).


### Local development (directly)

Stat the PostGIS database with docker-compose as shown above. Then install the dependencies:

- PostGIS (you use the one from docker-compose: `$ docker-compose up -d postgis`)
- GDAL
- Python 3.11.x
- Python packages with `$ pip install -r requirements.txt`
- Make local ESIDA Python package: `$ pip install -e .`
- Make the Flask App know to the system: `$ export FLASK_APP=esida`
- Run gunicorn to serve flask App: `$ gunicorn --bind 0.0.0.0:80 esida:app --error-logfile - --reload`
- Page can now be access via [http://localhost/](http://localhost/)
