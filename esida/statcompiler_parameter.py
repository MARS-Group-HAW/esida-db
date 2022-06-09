import os
import json
import datetime as dt
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

import numpy as np
import pandas as pd
import rasterio
import rasterio.mask
import fiona

from dbconf import get_engine
from esida.parameter import BaseParameter
from esida.models import Shape

class StatcompilerParameter(BaseParameter):
    """ Extends BaseParameter class for GeoTiff consumption. """

    def __init__(self):
        super().__init__()
        self.df = None

    def get_indicators(self):
        raise NotImplementedError

    def consume(self, df):
        raise NotImplementedError

    def extract(self):

        df = self.fetch_from_stat_compiler(self.get_indicators())

        # safe raw data
        data_dir = self.get_data_path()
        file = '{}_data_{}.csv'.format(dt.datetime.today().strftime('%Y-%m-%d_%H-%M-%S'), self.parameter_id)
        data_dir.mkdir(parents=True, exist_ok=True)
        df.to_csv(data_dir / file, index=False)

        return df


    def load(self, shapes=None, save_output=False):

        regions_df = pd.read_sql_query("SELECT id, name FROM shape WHERE type='region' ORDER by name", con=get_engine())


        # get raw data
        df = self.extract()

        # remove the generic / zone admin levels and only leave regions
        df['is_region'] = df['CharacteristicLabel'].apply(self.is_region)
        df = df[df['is_region'] == True]

        df['CharacteristicLabel'] = df['CharacteristicLabel'].apply(self.normalize_region_name)
        df['CharacteristicLabel'] = df['CharacteristicLabel'].apply(self.map_region_name_to_tz_stat_names)

        # group
        df = self.group_per_studyyear_region(df, self.get_indicators(), regions_df)

        # statcompiler specific data wrangling
        self.consume(df)


        self.save()


    def save(self):
        self.df.to_sql(self.parameter_id, get_engine(), if_exists='replace')

    def download(self, shape_id, start=None, end=None) -> pd.DataFrame:
        """ Statcompiler are only region based, so before we can load
        data we need to know, if we query a region (-> return directly) or
        if wie load a district. Then we need to query the parent region first.
        """

        shape = Shape.query.get(shape_id)
        if shape.type != 'region':
            shape_id = shape.parent_id

        return super().download(shape_id, start=start, end=end)

    # ---

    def is_region(self, name) -> bool:
        """ subnational breakdown Statcompiler seems to prepend actual regions
        with two dots (".."). """
        if name[0] == '.' and name[1] == '.':
            return True
        return False

    def normalize_region_name(self, name) -> str:
        return name.replace('..', '')

    def map_region_name_to_tz_stat_names(self, name) -> str:
        """ We use the names provided by the TZ bureau of statistics (partly swahili?).
        Statcompiler uses only english names and we have to map the two spellings. """

        if name == "Dar es Salaam":
            return "Dar-es-salaam"

        # Pemba island
        if name == "Pemba North":
            return "Kaskazini Pemba"

        if name == "Pemba South":
            return "Kusini Pemba"

        # Zanzibar island
        if name == "Town West":
            return "Mjini Magharibi"

        if name == "Zanzibar North":
            return "Kaskazini Unguja"

        if name == "Zanzibar South":
            return "Kusini Unguja"

        # Region splits

        # our db contains the latest 2016 districts/regions, so
        # we only map the values of the >2016 surveys to it.
        if name == "Mbeya (since 2016)":
            return "Mbeya"

        return name

    def fetch_from_stat_compiler(self, indicators) -> pd.DataFrame:
        # fetch data
        params = {
            # Country code
            'countryIds':      'TZ',
            # give region based level, still shows "zones" (tanzania)
            # we have to filter based on the prepended ".." in
            'breakdown':       'subnational',
            'indicatorIds':    ','.join(indicators),
            #'surveyIds':      'TZ2017MIS',
            'lang':            'en',
            'returnGeometry':  False,
            'surveyYearStart': 2010,
            'f':               'json',
        }

        data_url = 'https://api.dhsprogram.com/rest/dhs/data/?' + urlencode(params)

        # Obtain and Parse the list into a Python Object.
        req = urlopen(data_url)
        resp = json.loads(req.read())
        my_data = resp['Data']

        df = pd.DataFrame(my_data)

        return df

    def group_per_studyyear_region(self, df, indicators, regions_df):

        values = []

        # group by survey/year
        for sid in df['SurveyId'].unique():
            dfx = df[df['SurveyId'] == sid].reset_index()

            year = dfx.at[0, 'SurveyYear']

            for _, r in regions_df.iterrows():
                x = {
                    'year': year,
                    'shape_id': r['id'],
                    f'{self.parameter_id}_survey': sid,
                }

                for i in indicators:

                    # note absence of indicator in any case!
                    x[i] = None

                    dfxx = dfx[dfx['IndicatorId'] == i]

                    if len(dfxx) == 0:
                        # indicator not present for this study/year
                        self.logger.info('indicator not present for this study/year')
                        continue

                    # indicator for region
                    sri = dfxx.loc[dfxx['CharacteristicLabel'] == r['name']]

                    if len(sri) == 0:
                        self.logger.info('for this region no value exists: "%s"', r['name'])
                        # for this region no value exists
                        continue

                    sri = sri.reset_index()
                    x[i] = sri.at[0, 'Value']

                values.append(x)

        return pd.DataFrame(values)
