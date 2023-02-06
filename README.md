# ESIDA Data Hub

The Dat Hub is a Python based framework for downloading and calculating spatio-temporal data to different areas of interest, like administrative levels of a country, or other shapes. For example [Copernicus landusage raster data](https://lcviewer.vito.be/) could be used as input data, and adminstrave areas of a country could be used to calculate the proportion of each land type (crop land, forrest, …) in each adminstrative area.

<p align="center">
  <img src="./docs/Data%20Hub.png" alt="Visualization of the Data Hub flow of processing raw data" />
</p>

It aims to be a decision system for epidemiology and can provide an overview with socioecological per administrative level. It is developed in the context of the [ESIDA project](https://www.haw-hamburg.de/en/research/research-projects/project/project/show/esida/) and focused on Tanzania. But this framework aims to be agnostic to its data, so you can use it for different areas and data! See the section below about [setting up a different region](#use-your-own-geographic-region-and-data).

## Installation

### Dependencies & Software stack

The Data Hub uses the following software:

| Software                                                  | Remarks                                                      |
| --------------------------------------------------------- | ------------------------------------------------------------ |
| [Python 3](https://www.python.org/)                       | Programming language of the Data Hub                         |
| [GDAL](https://gdal.org/)                                 | Needed for spatial operations, like merging/cutting raster data |
| [PostGIS](https://postgis.net/install/)                   | Spatial database for storing region shapes and processed data |
| [Docker](https://www.docker.com/products/docker-desktop/) | Can be used to manage the other dependencies, without the need to install them yourself |
| [Jupyter](https://jupyter.org/)                           | Only needed for analysis of the raw data                     |

### Local setup (Docker)

> **Warning**  
> The Docker setup is recommended for using the Data Hub as it is provided, and not for changing regions/data. While it works, it's not a streamlined developing experience, due to need to rebuild the container after source changes. If this is your use-case you should go for the direct development setup explained below (though this requires installing a lot of dependencies locally).

Make sure you have [Docker](https://www.docker.com/products/docker-desktop/) installed and it's running. Clone the Data Hub repository and open it's directory in your CLI.

Build and start the containers:

    $ docker-compose up -d

The Data Hub is now available at [http://localhost/](http://localhost/) - though it is empty at the moment and not everything works. To set it up follow these steps: Open a CLI inside the Docker container (Docker GUI CLI or `$ docker-compose exec esida bash`) and run the following commands to create the database schema and import inital data. Those are only required to be run after the first setup.

````
# Inside Docker container CLI
$ flask create-db          # setup required database columns

$ python esida-cli.py init # import Tanzania region/district shape files into db

$ python ./esida-cli.py param meteo_tprecit extract # download and process precipitation data from Meteostat
$ python ./esida-cli.py param meteo_tprecit load
````

Further parameters can be loaded with the following commands, see `parameters/` folder oder the [listing in the web-frontend](http://localhost/parameters) for availbale parameter `key`s. After loading, you can use the download function for each shape or use the API to get the data (see Jupyter Notebook in folder `./notebooks/ESIDA DB Demo.ipynb`).

```
# Inside Docker container CLI
$ python ./esida-cli.py param <key> extract # downloads files from source
$ python ./esida-cli.py param <key> load    # processes source and saves to data
```

After this you can start/stop the containers with

    $ docker-compose start|stop

After you make changes to the source files, you need to rebuild the Docker container. For this follow these steps:

    $ docker-compose stop     # make sure the containers are not running
    $ docker-compose rm esida # remove the currently build container
    $ docker-compose up -d    # this should rebuild the container and reflect your code changes

### Local development (directly)

> **Note**  
> The local development setup is recommended for using the Data Hub with own data sources.

Make sure GDAL installed and Python 3 and the dependent packages are installed (`$ pip install -r requirements.txt` ). Due to the Geo-Dependencies this might be complicated. It might be easier to use the [Anaconda](https://www.anaconda.com/) distribution, which should install GDAL as well.

Make sure a PostGIS database is installed and accessable, in case you have installed Docker you can use PostGIS from the provided `docker-compose.yaml` file with: `$ docker-compose up -d postgis`.

Copy the file `.env.example` to `.env` and make sure the PostGIS settings are correct:

    $ cp .env.example .env

Also copy the contents of the folder`input/data.local/` to `input/data/`. This provides some default data for the Data Hub.

    $ rsync -a input/data.local/ input/data/

Setup the local Data Hub Python package with:

```
$ pip install -e .
$ export FLASK_APP=esida
```

Setup the database schema and import inital data:

```
$ flask create-db
$ python esida-cli.py init # import Tanzania region/district shape files into db
$ python ./esida-cli.py param meteo_tprecit extract
$ python ./esida-cli.py param meteo_tprecit load
```

Now you can start [gunicorn](https://gunicorn.org/) webserver (should be installed from the Python `requirements.txt`) and open the Data Hub at [http://localhost/](http://localhost/)

```
$ gunicorn --bind 0.0.0.0:80 esida:app --error-logfile - --reload
```



## Usage

### Access data

Two means of data access are provided. For all loaded shapes the available parameter data associated with it can be downloaded as CSV file. For each parameter a download containing all shapes for this parameter is provided as well. Those downloads can be accessed via the web frontend.

Also a simple REST like API is provided to query the shape and parameter data programmatically. See the Jupyter notebook [`notebooks/ESIDA DB Demo.ipynb`](notebooks/ESIDA DB Demo.ipynb) for further explanation and usage examples of the API.

Data quality metrics can be extracted as well with the API, for this see the notebook [`notebooks/ESIDA DB Data Quality.ipynb`](notebooks/ESIDA DB Data Quality.ipynb). In this case it is recommended to use the system locally since the queries for spatial data quality can be quite long-running, and it might not be possible to query them from a remote host.

### Use your own geographic region and data

The Data Hub can be used with any geographic areas, the areas can be organized hierarchically (i.e. administrative levels of a country). But the data need to be prepared in the format of the Data Hub before they can be used. See the [provided Jupyter Notebook](notebooks/Dat%20Hub%20Prepare%20Shapes.ipynb) on how to prepare a shape file for the Data Hub, this example uses Shape files from [GADM](https://gadm.org/download_country.html) which provides shape data for many countries of the world. After preparing the data you can import them with `$ python esida-cli.py load-shapes <path to shp file>`. You also need to define the `DATAHUB_SHAPE_TYPES` constant in the `.env` file with a space separated list of the categories/types of your shapes. For Germany this might look like `DATAHUB_SHAPE_TYPES="country state district"`.

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

After adapting the download links to your need, you can download and process the data with:

    $ python ./esida-cli.py param copernicus_crop extract # downloading weather station and data
    $ python ./esida-cli.py param copernicus_crop load    # calculating data for your imported shapes

All other `copernicus_*` parameters only need to execute the `load` command since the input data is shared between the layers.

### Extract data for arbitrary area

After ingesting data you can calculate the data for an arbitrary region inside the area of the imported data.

    $ python ./eisda-cli.py clip --wkt <path to WKT Polygon> [--abm]

This will generate a simulation blueprint with the required input data.

The `--abm` flag can be used to only export the relevant data needed for the MARS agent based model. You can store the Zip-file of your MARS model Box in `./input/data/MARS/`, so the Box will be included in the generated output folder automatically for easy usage.
