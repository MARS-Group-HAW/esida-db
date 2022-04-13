"""
Demographic Urban Settlement Extent optional

| Information     | Comment                                                      |
| --------------- | ------------------------------------------------------------ |
| Source          | [Worldpop]( https://www.worldpop.org/geodata/summary?id=17285) |
| Format          | `tiff`, 100 × 100 m                                          |
| Operation       | binary (0=not urban, 1=urban)                                |
| Temporal extent | 2010, 2020                                                   |

**Todo**:

- are `bsgme` and `bgsmi` the same parameter or different?

"""

import rasterio
import re
import os
import numpy as np
import pandas as pd

parameter_id = 'worldpop_bsgme'

def consume(file):
    x = re.search(r'[0-9]{4}', os.path.basename(file))
    year = int(x[0])

    dataset = rasterio.open(file)
    band1 = dataset.read(1, masked=True)

    total_cells = band1.count()
    set_cells = np.count_nonzero(band1==1)

    return {'value': set_cells / total_cells, 'year': year}

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
