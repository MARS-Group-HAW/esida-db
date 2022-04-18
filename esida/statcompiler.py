from urllib.parse import urlencode
from urllib.request import urlopen
import json
import pandas as pd

def is_region(name):
    """ subnational breakdown Statcompiler seems to prepend actual regions
    with two dots (".."). """
    if name[0] == '.' and name[1] == '.':
        return True
    return False

def normalize_region_name(name):
    return name.replace('..', '')

def map_region_name_to_tz_stat_names(name):
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

    # our db contains the lates 2016 districts/regions, so
    # we only map the values of the >2016 surveys to it.
    if name == "Mbeya (since 2016)":
        return "Mbeya"

    return name

def fetch_from_stat_compiler(indicators):
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

def group_per_studyyear_region(df, indicators, regions_df):

    values = []

    # group by survey/year
    for sid in df['SurveyId'].unique():
        dfx = df[df['SurveyId'] == sid].reset_index()

        year = dfx.at[0, 'SurveyYear']

        for _, r in regions_df.iterrows():
            x = {
                'survey': sid,
                'year':   year,
                'region_id': r['region_id'],
                'region_name': r['name'],
            }

            for i in indicators:

                # note absence of indicator in any case!
                x[i] = None

                dfxx = dfx[dfx['IndicatorId'] == i]

                if len(dfxx) == 0:
                    # indicator not present for this study/year
                    print('indicator not present for this study/year')
                    continue

                # indicator for region
                sri = dfxx.loc[dfxx['CharacteristicLabel'] == r['name']]

                if len(sri) == 0:
                    print('for this region no value exists: "{}"'.format(r['name']))
                    # for this region no value exists
                    continue

                sri = sri.reset_index()
                x[i] = sri.at[0, 'Value']

            values.append(x)

    return pd.DataFrame(values)