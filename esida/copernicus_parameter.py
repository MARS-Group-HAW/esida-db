
import os
import re
import subprocess
from pathlib import Path
from urllib.parse import urlparse

import numpy as np

from esida.tiff_parameter import TiffParameter

class CopernicusParameter(TiffParameter):
    """ Extends TiffParameter class for Copernicus consumption. """

    def __init__(self):
        super().__init__()

        self.is_percent = True

        self.area_of_interest = []

        self.mapping = [{
            "meaning": "unknown",
            "value": 0
        },
        {
            "meaning": "ENF_closed",
            "value": 111
        },
        {
            "meaning": "EBF_closed",
            "value": 112
        },
        {
            "meaning": "DNF_closed",
            "value": 113
        },
        {
            "meaning": "DBF_closed",
            "value": 114
        },
        {
            "meaning": "mixed_closed",
            "value": 115
        },
        {
            "meaning": "unknown_closed",
            "value": 116
        },
        {
            "meaning": "ENF_open",
            "value": 121
        },
        {
            "meaning": "EBF_open",
            "value": 122
        },
        {
            "meaning": "DNF_open",
            "value": 123
        },
        {
            "meaning": "DBF_open",
            "value": 124
        },
        {
            "meaning": "mixed_open",
            "value": 125
        },
        {
            "meaning": "unknown_open",
            "value": 126
        },
        {
            "meaning": "shrubland",
            "value": 20
        },
        {
            "meaning": "herbaceous_vegetation",
            "value": 30
        },
        {
            "meaning": "cropland",
            "value": 40
        },
        {
            "meaning": "built-up",
            "value": 50
        },
        {
            "meaning": "bare_sparse_vegetation",
            "value": 60
        },
        {
            "meaning": "snow_ice",
            "value": 70
        },
        {
            "meaning": "permanent_inland_water",
            "value": 80
        },
        {
            "meaning": "herbaceous_wetland",
            "value": 90
        },
        {
            "meaning": "moss_lichen",
            "value": 100
        },
        {
            "meaning": "sea",
            "value": 200
        }]

    def get_data_path(self) -> Path:
        """ Overwrite parameter_id based input directory, because we have
        multiple derives parameters from this source. """
        return Path(f"./input/data/copernicus_landcover/")

    def extract(self):
        # Todo: we could dynamically download the needed for the requested shape
        # but for now we just download the 2 required tiles for tanzania.

        # The data are provided as single download for the complete world
        # that is ~1.7 GB (compressed!), but are also provided as single tiles.
        # For Tanzania wee need to tiles, see: https://lcviewer.vito.be/download
        tiles = {
            'E020N00': [
                'https://s3-eu-west-1.amazonaws.com/vito.landcover.global/v3.0.1/2015/E020N00/E020N00_PROBAV_LC100_global_v3.0.1_2015-base_Discrete-Classification-map_EPSG-4326.tif',
                'https://s3-eu-west-1.amazonaws.com/vito.landcover.global/v3.0.1/2016/E020N00/E020N00_PROBAV_LC100_global_v3.0.1_2016-conso_Discrete-Classification-map_EPSG-4326.tif',
                'https://s3-eu-west-1.amazonaws.com/vito.landcover.global/v3.0.1/2017/E020N00/E020N00_PROBAV_LC100_global_v3.0.1_2017-conso_Discrete-Classification-map_EPSG-4326.tif',
                'https://s3-eu-west-1.amazonaws.com/vito.landcover.global/v3.0.1/2018/E020N00/E020N00_PROBAV_LC100_global_v3.0.1_2018-conso_Discrete-Classification-map_EPSG-4326.tif',
                'https://s3-eu-west-1.amazonaws.com/vito.landcover.global/v3.0.1/2019/E020N00/E020N00_PROBAV_LC100_global_v3.0.1_2019-nrt_Discrete-Classification-map_EPSG-4326.tif',
            ],
            'E040N00': [
                'https://s3-eu-west-1.amazonaws.com/vito.landcover.global/v3.0.1/2015/E040N00/E040N00_PROBAV_LC100_global_v3.0.1_2015-base_Discrete-Classification-map_EPSG-4326.tif',
                'https://s3-eu-west-1.amazonaws.com/vito.landcover.global/v3.0.1/2016/E040N00/E040N00_PROBAV_LC100_global_v3.0.1_2016-conso_Discrete-Classification-map_EPSG-4326.tif',
                'https://s3-eu-west-1.amazonaws.com/vito.landcover.global/v3.0.1/2017/E040N00/E040N00_PROBAV_LC100_global_v3.0.1_2017-conso_Discrete-Classification-map_EPSG-4326.tif',
                'https://s3-eu-west-1.amazonaws.com/vito.landcover.global/v3.0.1/2018/E040N00/E040N00_PROBAV_LC100_global_v3.0.1_2018-conso_Discrete-Classification-map_EPSG-4326.tif',
                'https://s3-eu-west-1.amazonaws.com/vito.landcover.global/v3.0.1/2019/E040N00/E040N00_PROBAV_LC100_global_v3.0.1_2019-nrt_Discrete-Classification-map_EPSG-4326.tif',
            ]
        }

        for tile, urls in tiles.items():
            for url in urls:
                self._save_url_to_file(url, folder=self.get_data_path()/tile)

        # We create one tiff based of the two tiles so further in the processing
        # pipeline we don't need to handle checking/merging data from different
        # tiles.
        # be aware, that the gdal_merge.py utility will not retain the color meta
        # information provided by copernicus.
        try:
            for i, year in enumerate(range(2015, 2019 + 1)):
                in_file1 = self.get_data_path() / "E020N00" / os.path.basename(urlparse(tiles['E020N00'][i]).path)
                in_file2 = self.get_data_path() / "E040N00" / os.path.basename(urlparse(tiles['E040N00'][i]).path)
                out_file = self.get_data_path() / f"Copernicus_Tanzania_{year}-base_Discrete-Classification.tif"

                # if merged file already exists, don't merge again
                if os.path.isfile(out_file):
                    continue

                subprocess.check_output([
                    'gdal_merge.py',
                    "-o", out_file,

                    # input files
                    in_file1,
                    in_file2,

                    "-n", "255", # NoData for consumption
                    "-a_nodata", "255", # write NotData to out file
                ])
            return True
        except subprocess.CalledProcessError as error:
            self.logger.warning("Could not merge file: %s, %s", url, error.stderr)

    def get_value_for_key(self, key) -> int:
        """ Returns the value used for a land usage key. """
        for item in self.mapping:
            if item['meaning'] == key:
                return item['value']

        raise ValueError(f"Unknown Copernicus mapping key: {key}.")

    def consume(self, file, band, shape):
        x = re.search(r'([0-9]{4})', os.path.basename(file))
        year = int(x[1])

        total_cells = np.count_nonzero(~np.isnan(band))
        values, count = np.unique(band, return_counts=True)
        stats = dict(zip(values, count))

        aoi_cells = 0
        for key in self.area_of_interest:
            val = self.get_value_for_key(key)

            if val in stats:
                aoi_cells += stats[val]

        self.rows.append({
            'year': year,
            'shape_id': shape['id'],
            f'{self.parameter_id}': aoi_cells / total_cells,
        })
