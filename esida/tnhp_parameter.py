import json
import urllib.request
import datetime as dt
from pathlib import Path

import pandas as pd

from esida.parameter import BaseParameter

class TnhpParameter(BaseParameter):
    """ Extends BaseParameter class for TANZANIA NATIONAL HEALTH PORTAL
    MINISTRY OF HEALTH. """

    def get_data_path(self) -> Path:
        """ Overwrite parameter_id based input directory, because we have
        multiple derives parameters from this source. """
        return Path("./input/data/tnhp/")

    def extract(self):
        """ (E)xtract: automatic download of source files. """

        def find_name_for_key(data, key):
            """ row / cal names are referenced by id's an can be "resolved
            int the meteData section. """
            if key in data['metaData']['items']:
                return data['metaData']['items'][key]['name']

            return None

        url = "https://hmisportal.moh.go.tz/portal-middleware-live/api/analytics.json?" \
        "dimension=ou:m0frOspS7JY;LEVEL-2&dimension=dx:lJNzLghsdKg;UxnVJil2BwF;nG4jLoeBLAN;" \
        "fdX6lREQQp0;oRbPiu3t4oc;BwXD0MzkvLG&filter=pe:{year}&includeMetadataDetails=true"

        dfs = []
        for year in range(2013, 2023):
            with urllib.request.urlopen(url.format(year=year)) as req:
                data = json.loads(req.read().decode())

            data_prep = []

            for row in data['rows']:
                data_prep.append({
                    'year':     year,
                    'function': find_name_for_key(data, row[0]),
                    'region':   find_name_for_key(data, row[1]),
                    'value':    row[2]
                })

            dfs.append(pd.DataFrame(data_prep))

        df = pd.concat(dfs)
        df['value'] = pd.to_numeric(df['value'])

        self.get_data_path().mkdir(parents=True, exist_ok=True)

        now = dt.datetime.now()
        file_name = f"{now.strftime('%Y-%m-%d_%H-%M-%S')}_tnhp.csv"
        df.to_csv(self.get_data_path() / file_name, index=False)
