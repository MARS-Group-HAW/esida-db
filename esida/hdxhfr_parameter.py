import os
import subprocess
from pathlib import Path
from urllib.parse import urlparse

import fiona
import geopandas
import pandas as pd
from sqlalchemy.sql import text

from dbconf import get_engine
from esida.parameter import BaseParameter

class HdxhfrParameter(BaseParameter):
    """ Extends BaseParameter class for HDX Health facility data """

    def __init__(self):
        super().__init__()

        self.facility_types = None

        # table name for the cleaned records
        self.table_name_all = 'hdxhfr'
        self.table_name = f"data_{self.parameter_id}"

        self.precision = 0

    # ---

    def get_parameter_path(self) -> Path:
        return Path(f"./input/data/hdx_hfr/")

    def extract(self):

        # unsure if the URL is permanent, prefer local copy
        url = "https://data.humdata.org/dataset/eb1ba830-9464-43c8-9370-28cee0c99f5d/resource/341668a3-7066-46e4-aca0-fe09c57f9314/download/suhsharan_health_facilities.zip"
        self._save_url_to_file(url)

        # Check if file is already unzipped
        a = urlparse(url)
        file_name = os.path.basename(a.path)
        if os.path.isfile(self.get_parameter_path() / "sub-saharan_health_facilities.shp"):
            self.logger.debug("File already unzipped.")
        else:
            try:
                # cmd syntax didn't work, not sure why
                #subprocess.check_output('gzip -d ./input/data/chc_chirps/*.gz', shell=True)
                in_file = self.get_parameter_path() / file_name
                out_dir = self.get_parameter_path().as_posix()
                subprocess.run(f'unzip {in_file} -d {out_dir}', shell=True,
                    capture_output=True, check=True)
            except subprocess.CalledProcessError as error:
                self.logger.warning("Could not unzip files: %s", error.stderr)


        gdf = geopandas.read_file(self.get_parameter_path() / "sub-saharan_health_facilities.shp")
        gdf = gdf[gdf['Country'] == 'Tanzania']

        gdf = gdf.reset_index(drop=True)
        gdf.insert(0, 'id', gdf.index)

        gdf.to_postgis(self.table_name_all, con=get_engine(), if_exists='replace')

    def load(self, shapes=None, save_output=False):

        if shapes is None:
            shapes = self._get_shapes_from_db()

        # create view
        sql = text(f"""CREATE OR REPLACE VIEW {self.table_name} AS
        SELECT *
        FROM {self.table_name_all}
        WHERE "Facility t" IN :values""")

        engine = get_engine()
        with engine.connect() as con:
            res = con.execute(sql, values=tuple(self.facility_types))

        # load all known facilities with types of interest
        gdf = geopandas.read_postgis(f"SELECT * FROM {self.table_name}",
                            geom_col='geometry', con=get_engine())

        rows = []

        for shape in shapes:
            self.logger.debug("loading shape: %s", shape['name'])

            if "geometry" in shape:
                mask = [shape['geometry']]
            elif "file" in shape:
                with fiona.open(shape['file'], "r") as shapefile:
                    mask = [feature["geometry"] for feature in shapefile]
            else:
                raise ValueError("No geometry found for given shape.")

            if len(mask) != 1:
                self.logger.warning("Shape contains more than one geometry, using the first.")

            # clip to only facilities within area of interest
            gdfx = gdf[gdf['geometry'].within(mask[0])]

            # year -> 2022, see metadata https://data.humdata.org/dataset/health-facilities-in-sub-saharan-africa
            rows.append({
                'year':      2022,
                'shape_id': shape['id'],
                f"{self.parameter_id}": len(gdfx)
            })

        df = pd.DataFrame(rows)
        df.to_sql(self.parameter_id, con=get_engine(), if_exists='replace')
