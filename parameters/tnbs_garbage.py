import geopandas
import pandas as pd

from esida.parameter import BaseParameter

from dbconf import get_engine

class tnbs_garbage(BaseParameter):

    def __init__(self):
        super().__init__()
        self.is_percent = True

    def extract(self):
        # Nothing to do here, manually prepared excel file, extracted from
        # 2012 census
        pass

    def load(self, shapes=None, save_output=False):
        df = pd.read_excel(self.get_data_path() / 'S 202 Table 12.12- Percentage of Households by Region and Type of Refuse Disposal.xlsx',
                        skiprows=3)

        regions_gdf = geopandas.GeoDataFrame.from_postgis("SELECT * FROM shape WHERE type IN ('country', 'region')",
            geom_col='geometry', con=get_engine())
        regions = dict(zip(regions_gdf.name, regions_gdf.id))


        rows = []

        for _, row in df.iterrows():
            name = row['Region']

            if name == 'Dar es Salaam':
                name = 'Dar-es-salaam'

            if name not in regions:
                #print(name)
                continue

            rows.append({
                'shape_id': regions[name],
                'year': 2012,
                f'{self.parameter_id}': (row['Regularly\nCollected'] + row['Irregularly\nCollected']) / 100
            })

        self.df = pd.DataFrame(rows)


        self.save()
