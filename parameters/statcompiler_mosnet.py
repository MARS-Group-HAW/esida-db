import pandas as pd

from esida.statcompiler_parameter import StatcompilerParameter
from dbconf import get_engine

class statcompiler_mosnet(StatcompilerParameter):

    def get_indicators(self):
        return ['ML_NETP_H_MOS' ]

    def append_preliminary2022(self):
        """
        As of now (April-2023) the latest DHS Survey for Tanzania is still ongoing
        and not yet accessible via the STATcompiler API.

        The preliminary results are already available at:
        - https://dhsprogram.com/methodology/survey/survey-display-578.cfm
        - https://www.nbs.go.tz/index.php/en/census-surveys/health-statistics/demographic-and-health-survey-dhs/831-dhs-2022-key-indicators-report

        Until the data appear in the API we append those results manually to the
        API results for the previous surveys.
        """

        df = pd.read_csv(self.get_data_path() / 'TZ2022DHS_Preliminary_Insecticide_treated_nets.csv')
        df['region'] = df['region'].apply(self.map_region_name_to_tz_stat_names)

        regions_df = pd.read_sql_query("SELECT id, name FROM shape WHERE type='region' ORDER by name", con=get_engine())

        rows = []

        for _, r in regions_df.iterrows():

            sri = df.loc[df['region'] == r['name']].reset_index()

            if len(sri) == 0:
                self.logger.info('for this region no value exists: "%s"', r['name'])
                # for this region no value exists
                continue

            rows.append({
                'year': 2022,
                'shape_id': r['id'],
                f'{self.parameter_id}_survey': "TZ2022DHS_Preliminary",
                f'{self.parameter_id}': sri.at[0, 'percentage_of_households_with_itn'],
                'ML_NETP_H_MOS': sri.at[0, 'percentage_of_households_with_itn']
            })

        return pd.DataFrame(rows)


    def consume(self, df):
        df[f'{self.parameter_id}'] = df[self.get_indicators()].mean(axis=1)
        self.df = df

        self.df = pd.concat([self.df, self.append_preliminary2022()])
