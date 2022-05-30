"""
Demographic	Population counts


- tiff 100 x 100 m
- sum total number
- Annualy (2010-2020)
- [Worldpop](https://www.worldpop.org/geodata/listing?id=69)

"""

import rasterio
import rasterio.mask
import fiona
import re
import os
import numpy as np
import pandas as pd

from esida.parameter import BaseParameter
from dbconf import get_engine

class worldpop_popc(BaseParameter):

    def extract(self):
        for year in range(2010, 2020+1):
            url = f"https://data.worldpop.org/GIS/Population/Global_2000_2020/{year}/TZA/tza_ppp_{year}_UNadj.tif"
            self._save_url_to_file(url)


    def load(self, shapes, save_output=False):
        param_dir = self.get_data_path()
        files = sorted([s for s in os.listdir(param_dir) if s.rpartition('.')[2] in ('tiff','tif')])

        for file in files:
            self.logger.info("loading file: %s", file)

            x = re.search(r'[0-9]+', os.path.basename(file))
            year = int(x[0])

            with rasterio.open(param_dir / file) as src:
                for shape in shapes:
                    self.logger.debug("loading shape: %s", shape['file'])

                    nodata = src.nodata

                    if nodata is None:
                        raise ValueError(f"No NoData value for GeoTiff {file}")

                    with fiona.open(shape['file'], "r") as shapefile:
                        mask = [feature["geometry"] for feature in shapefile]

                    out_image, out_transform = rasterio.mask.mask(src, mask, crop=True, nodata=nodata)
                    out_meta = src.meta

                    band1 = out_image[0]
                    band1[band1==nodata] = np.nan

                    self.rows.append({
                        f"{self.parameter_id}_sum": np.nansum(band1),
                        'year': year,
                        'shape_id': shape['id']
                    })


        df = pd.DataFrame(self.rows)
        #df.to_csv('wtf.csv')
        df.to_sql(self.parameter_id, get_engine(), if_exists='replace')

def to_sql(rows, engine):
    df = pd.DataFrame(rows)
    df.to_sql(parameter_id, engine)

def download(shape_id, engine):
    sql = "SELECT year, value as {} FROM {} WHERE district_id = {}".format(
        parameter_id, parameter_id,
        shape_id
    )

    df = pd.read_sql_query(sql, con=engine)

    return df


