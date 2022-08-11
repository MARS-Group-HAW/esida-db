import os
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
import rasterio.mask
import fiona
from rasterstats import zonal_stats

from dbconf import get_engine
from esida.parameter import BaseParameter

class TiffParameter(BaseParameter):
    """ Extends BaseParameter class for GeoTiff consumption. """

    def __init__(self):
        super().__init__()
        self.manual_nodata = None

    def consume(self, file, band, shape):
        raise NotImplementedError

    def get_tiff_files(self, param_dir):
        files = sorted([s for s in os.listdir(param_dir) if s.rpartition('.')[2] in ('tiff','tif')])

        return files


    def load(self, shapes=None, save_output=False, param_dir=None):

        if param_dir is None:
            param_dir = self.get_data_path()

        files = self.get_tiff_files(param_dir)

        if shapes is None:
            shapes = self._get_shapes_from_db()

        file_count = len(files)
        i = 1

        for file in files:
            self.logger.info("loading file (%s of %s): %s", i, file_count, file)
            i += 1

            with rasterio.open(param_dir / file) as src:
                nodata = src.nodata
                self.logger.debug("No data is: %s", nodata)

                # GeoTiff has NO NoData meta data set, try to use custom
                # set NoData value
                if nodata is None:
                    nodata = self.manual_nodata

                # make sure manual_nodata is set
                if nodata is None:
                    raise ValueError(f"No NoData value for GeoTiff {file}")

                for shape in shapes:
                    self.logger.debug("loading shape: %s", shape['name'])

                    if "geometry" in shape:
                        mask = [shape['geometry']]
                    elif "file" in shape:
                        with fiona.open(shape['file'], "r") as shapefile:
                            mask = [feature["geometry"] for feature in shapefile]
                    else:
                        raise ValueError("No geometry found for given shape.")

                    out_image, out_transform = rasterio.mask.mask(src, mask, crop=True, nodata=nodata)
                    out_meta = src.meta

                    if save_output:
                        out_meta.update({"driver": "GTiff",
                                        "height": out_image.shape[1],
                                        "width": out_image.shape[2],
                                        "transform": out_transform})

                        out_file = self.get_output_path() / self.parameter_id / file
                        Path(os.path.dirname(out_file)).mkdir(parents=True, exist_ok=True)
                        with rasterio.open(out_file, "w", **out_meta) as dest:
                            dest.write(out_image)

                    band1 = out_image[0]

                    # To mask NoData cells we use np.nan so we can use np.nan*-methods.
                    # But np.nan is only available inside float arrays, not with
                    # int arrays!
                    # So in case we have a int array GeoTiff, we need to check
                    # and convert it to a float array.
                    if np.issubdtype(band1.dtype, np.integer):
                        band1 = band1.astype(np.float32)

                    band1[band1==nodata] = np.nan

                    self.consume(file, band1, shape)

        self.save()


    def da_spatial(self, shape_id=None):

        if not self.is_loaded():
            return None

        files = self.get_tiff_files(self.get_data_path())

        shapes = self._get_shapes_from_db(shape_id)

        file_count = len(files)
        i = 1

        masks = []
        for shape in shapes:
            self.logger.debug("loading shape: %s", shape['name'])

            if "geometry" in shape:
                mask = [shape['geometry']]
            elif "file" in shape:
                with fiona.open(shape['file'], "r") as shapefile:
                    mask = [feature["geometry"] for feature in shapefile]
            else:
                raise ValueError("No geometry found for given shape.")

            masks.append(mask[0])

        results = []

        for file in files:
            self.logger.info("loading file (%s of %s): %s", i, file_count, file)
            i += 1
            stats = zonal_stats(masks, self.get_data_path() / file, stats=['nodata', 'count'], nodata=self.manual_nodata)

            for j, s in enumerate(stats):
                r = {
                    'parameter_id': self.parameter_id,
                    'file': file,
                    'coverage': s['count'] / (s['count'] + s['nodata']),
                    'valid_cells': s['count'],
                    'nodata_cells': s['nodata'],
                    'shape_id': shapes[j]['id']
                }
                results.append(r)

        df = pd.DataFrame(results)
        result = df['coverage'].mean()

        return (result, results)

