# ESIDA Data Hub

The Data Hub is a Python based framework for downloading and calculating spatio-temporal data to different areas of interest, like administrative levels of a country, or other shapes. For example [Copernicus land usage raster data](https://lcviewer.vito.be/) could be used as input data, and administrative areas of a country could be used to calculate the proportion of each land type (crop land, forest, …) in each administrative area.

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

Make sure you have [Docker](https://www.docker.com/products/docker-desktop/) installed, and it's running. Clone the Data Hub repository and open the directory in your CLI.

Build and start the containers:

    $ docker-compose up -d

The Data Hub is now available at [http://localhost/](http://localhost/) - though it is empty at the moment and not everything works. To set it up follow these steps:

````
# setup required database columns
$ docker-compose exec esida flask create-db          

# import Tanzania region/district shape files into db
$ docker-compose exec esida python ./esida-cli.py load-shapes ./input/shapes/esida_tza.gpkg

# download and process precipitation data from Meteostat
$ docker-compose exec esida python ./esida-cli.py param meteo_tprecit extract
$ docker-compose exec esida python ./esida-cli.py param meteo_tprecit load
````

Further Data Layers can be loaded with the following commands, see `parameters/` folder or the [listing in the web-frontend](http://localhost/parameters) for available parameter `key`s. After loading, you can use the download function for each shape or use the API to get the data (see Jupyter Notebook in folder [`./notebooks/ESIDA DB Demo.ipynb`](notebooks/ESIDA%20DB%20Demo.ipynb)).

```
$ docker-compose exec esida python ./esida-cli.py param <key> extract # downloads files from source
$ docker-compose exec esida python ./esida-cli.py param <key> load    # processes source and saves to data
```

After this you can start/stop the containers with

    $ docker-compose start|stop

### Local development (directly)

In case you want to install the Data Hub directly with its dependencies follow these instructions:

<details>
 <summary>Manual installation</summary>

Make sure GDAL installed and Python 3 and the dependent packages are installed (`$ pip install -r requirements.txt`). Due to the Geo-Dependencies this might be complicated. It might be easier to use the [Anaconda](https://www.anaconda.com/) distribution, which should install GDAL as well. You need postgresql client tools as well for building SQLAlchemy, on macOS run `brew install libpq`.

Make sure a PostGIS database is installed and accessible, in case you have installed Docker you can use PostGIS from the provided `docker-compose.yaml` file with: `$ docker-compose up -d postgis`.

Copy the file `.env.example` to `.env` and make sure the PostGIS settings are correct:

    $ cp .env.example .env

Also copy the contents of the folder`input/data.local/` to `input/data/`. This provides some default data for the Data Hub.

    $ rsync -a input/data.local/ input/data/

Set up the local Data Hub Python package with:

```
$ pip install -e .
$ export FLASK_APP=esida
```

Set up the database schema and import initial data:

```
$ flask create-db
$ python esida-cli.py init # import Tanzania region/district shape files into db
$ python ./esida-cli.py param meteo_tprecit extract
$ python ./esida-cli.py param meteo_tprecit load
```

Now you can start [gunicorn](https://gunicorn.org/) web server (should be installed from the Python `requirements.txt`) and open the Data Hub at [http://localhost/](http://localhost/)

```
$ gunicorn --bind 0.0.0.0:80 esida:app --error-logfile - --reload
```

#### Common pitfalls

<details>
<summary>Python exceptions like `Library not loaded: '[…]/gdal/lib/libgdal.xy.dylib'`</summary>

If you get Python exceptions like `Library not loaded: '[…]/gdal/lib/libgdal.xy.dylib'` you have probably updated your GDAL installation and some Python packages can't find it anymore. You need to clear pip's cache and rebuild the packages:

```
pip cache purge
pip install -r requirements.txt --upgrade --force-reinstall
```
</details>

</details>



## Usage

### Access data

Two means of data access are provided. For all loaded shapes the available parameter data associated with it can be downloaded as CSV file. For each parameter a download containing all shapes for this parameter is provided as well. Those downloads can be accessed via the web frontend.

Also a simple REST like API is provided to query the shape and parameter data programmatically. See the Jupyter notebook [`notebooks/ESIDA DB Demo.ipynb`](notebooks/ESIDA%20DB%20Demo.ipynb) for further explanation and usage examples of the API.

Data quality metrics can be extracted as well with the API, for this see the notebook [`notebooks/ESIDA DB Data Quality.ipynb`](notebooks/ESIDA%20DB%20Data%20Quality.ipynb). In this case it is recommended to use the system locally since the queries for spatial data quality can be quite long-running, and it might not be possible to query them from a remote host.

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

#### Copernicus Land usage

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



## Contributions

Software Originator: Jonathan Ströbele

Operational Development: Jonathan Ströbele, Kristopher Nolte, Juliane Boenecke, Dr Matthias H. Belau, Dr Ulfia A. Lenfers, Prof Dr Thomas Clemen

Supervisor: Prof Dr Thomas Clemen / MARS Group, HAW Hamburg

Conceptual Framework Development: ESIDA Consortium (alphabetic order: Prof Amena Almes Ahmad<sup>1</sup>, Nima Ahmady-Moghaddam<sup>2</sup>, Prof Dr Heiko Becher<sup>3</sup>, Dr Matthias Hans Belau<sup>4</sup>, Juliane Boenecke<sup>1,2,5</sup>, Dr Johanna Brinkel<sup>5,6</sup>, Prof Dr Thomas Clemen<sup>2,7</sup>, Daria Dretvić<sup>8</sup>, Dr Mirko Himmel<sup>8</sup>, Dr Katharina Sophia Kreppel<sup>9,10</sup>, Prof Dr Dr Walter Leal Filho<sup>11,12</sup>, Dr Ulfia Annette Lenfers<sup>2</sup>, Prof Dr Jürgen May<sup>5,6,13</sup>, Ummul-Khair Mustafa<sup>9,14</sup>, Dr Devotha Godfrey Nyambo<sup>7</sup>, Luba Pascoe<sup>7</sup>, Jennifer Louise Pohlmann<sup>11</sup>, Prof Dr Ralf Reintjes<sup>1,15</sup>, Dr Elingarami Sauli<sup>9</sup>, Prof Dr Wolfgang Streit<sup>8</sup>, Jonathan Ströbele<sup>2</sup>)

The Data Hub was developed within the framework of the ESIDA research and network project (Epidemiological Surveillance for Infectious Diseases in Subsaharan Africa). ESIDA received funding from the German Federal Ministry of Education and Research (BMBF 01DU20005) under the CONNECT (connect-education-research-innovation) funding scheme.

<sup>1</sup> Department of Health Sciences, Faculty of Life Sciences, Hamburg University of Applied Sciences, Hamburg, Germany  
<sup>2</sup> Department of Computer Sciences, Faculty of Engineering and Computer Science, Hamburg University of Applied Sciences, Hamburg, Germany  
<sup>3</sup> Unit of Epidemiology and Biostatistics, Heidelberg Institute of Global Health, Heidelberg University Hospital, Heidelberg, Germany  
<sup>4</sup> Institute of Medical Biometry and Epidemiology, University Medical Center Hamburg-Eppendorf, Hamburg, Germany  
<sup>5</sup> Department of Infectious Disease Epidemiology, Bernhard Nocht lnstitute for Tropical Medicine, Hamburg, Germany  
<sup>6</sup> German Center for Infection Research (DZIF), Hamburg, Germany  
<sup>7</sup> School of Computational and Communication Science and Engineering, Nelson Mandela African Institution of Science and Technology, Arusha, Tanzania  
<sup>8</sup> Department for Microbiology and Biotechnology, Institute for Plant Sciences and Microbiology, University of Hamburg, Hamburg, Germany  
<sup>9</sup> School of Life Sciences and Bioengineering, Nelson Mandela African Institution of Science and Technology, Arusha, Tanzania  
<sup>10</sup> Department of Public Health, Institute of Tropical Medicine Antwerpen, Antwerpen, Belgium  
<sup>11</sup> Research and Transfer Centre “Sustainable Development and Climate Change Management” (FTZ-NK), Department of Health Sciences, Faculty of Life Sciences, Hamburg University of Applied Sciences, Hamburg, Germany  
<sup>12</sup> Manchester Metropolitan University, School of Science and the Environment, Manchester, United Kingdom  
<sup>13</sup> Department of Tropical Medicine I, University Medical Center Hamburg-Eppendorf (UKE), Hamburg, Germany  
<sup>14</sup> Department of Biological Sciences, Dar es Salaam University College of Education, Dar es Salaam, Tanzania  
<sup>15</sup> Health Sciences Unit, Faculty of Social Sciences, Tampere University, Tampere, Finland  
