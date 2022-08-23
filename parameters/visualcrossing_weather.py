import os
import subprocess
from urllib.parse import urlparse
import datetime as dt

import fiona
import geopandas
import pandas as pd
from decouple import config

from esida.parameter import BaseParameter

from dbconf import get_engine

class visualcrossing_weather(BaseParameter):

    def __init__(self):
        super().__init__()
        self.time_col = 'date'

    def extract(self):
        url = "https://www.fao.org/giews/earthobservation/asis/data/country/TZA/MAP_ASI/DATA/ASI_Dekad_Season1_data.csv"
        self._save_url_to_file(url)

    def _build_api_url(self, lat: float, lng: float, start: dt.datetime, end: dt.datetime) -> str:

        # This is the core of our weather query URL
        BaseURL = 'https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/'

        ApiKey = config('VISUALCROSSING_API_KEY', default='', cast=str)

        if len(ApiKey) == 0:
            raise Exception("Missing VisualCrossing API key")

        #UnitGroup sets the units of the output - us or metric
        UnitGroup = 'metric'

        #Location for the weather data
        Location = f"{lat},{lng}"

        #Optional start and end dates
        #If nothing is specified, the forecast is retrieved.
        #If start date only is specified, a single historical or forecast day will be retrieved
        #If both start and and end date are specified, a date range will be retrieved
        StartDate = start.strftime("%Y-%m-%d")
        EndDate   = end.strftime("%Y-%m-%d")

        #JSON or CSV
        #JSON format supports daily, hourly, current conditions, weather alerts and events in a single JSON package
        #CSV format requires an 'include' parameter below to indicate which table section is required
        ContentType="csv"

        #include sections
        #values include days,hours,current,alerts
        Include="days"

        #basic query including location
        ApiQuery = BaseURL + Location

        ApiQuery += "/" + StartDate
        ApiQuery += "/" + EndDate

        # Url is completed. Now add query parameters (could be passed as GET or POST)
        ApiQuery+="?"

        #append each parameter as necessary
        if (len(UnitGroup)):
            ApiQuery += "&unitGroup=" + UnitGroup

        if (len(ContentType)):
            ApiQuery += "&contentType=" + ContentType

        if (len(Include)):
            ApiQuery += "&include=" + Include

        ApiQuery += "&key=" + ApiKey

        return ApiQuery

    def load(self, shapes=None, save_output=False):

        if shapes is None:
            shapes = self._get_shapes_from_db()

        dfs = []

        for shape in shapes:

            if "geometry" in shape:
                mask = [shape['geometry']]
            elif "file" in shape:
                with fiona.open(shape['file'], "r") as shapefile:
                    mask = [feature["geometry"] for feature in shapefile]
            else:
                raise ValueError("No geometry found for given shape.")

            centroid = mask[0].centroid

            today = dt.datetime.today()
            start = today - dt.timedelta(days=1)
            end   = today + dt.timedelta(days=1)

            query = self._build_api_url(lat=centroid.y, lng=centroid.x, start=start, end=end)

            df = pd.read_csv(query)
            dfs.append(df)

        self.df = pd.concat(dfs)

        # MARS needs a column to map a geometry and the value
        # so we add a column to join with
        self.df['spatial_join_col'] = 1

        self.save()
