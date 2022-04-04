import os
import pandas as pd

import importlib
import pkgutil
from db import get_engine

engine  = get_engine()
outputs = sorted(os.listdir("./output/"))
params  = [name for _, name, _ in pkgutil.iter_modules(['parameters'])]
params  = ['worldpop_bsgme']


cwd = os.getcwd()
df = pd.read_sql_query('SELECT gid, newdist20 FROM districts', con=engine)

# loop over all defined parameters
for p in params:
    pm = importlib.import_module('parameters.{}'.format(p))

    rows = []

    for index, row in df.iterrows():
        shape="NewDist20_{}".format(row['newdist20']) # reconstruct output folder name
        shape_out_dir = os.path.join(cwd, 'output', shape)

        if not os.path.isdir(shape_out_dir):
            continue

        param_dir = os.path.join(shape_out_dir, p)

        if os.path.isdir(param_dir):
            # multiple files per parameter for multiple years
            files = sorted(os.listdir(param_dir))
            for f in files:
                s  = pm.consume(os.path.join(param_dir, f))
                s['district_id'] = row['gid']
                rows.append(s)
                print("\t{} - ".format(f) + str(s))
        else:
            print("no feature for {}".format(shape))

    pm.to_sql(rows, engine)



    # -> directory based listing
    #for shape in outputs:
    #    shape_out_dir = os.path.join(cwd, 'output', shape)
    #    if not os.path.isdir(shape_out_dir):
    #        continue
    #
    #    # worldpop_popc
    #    worldpop_popc_dir = os.path.join(shape_out_dir, 'worldpop_popc')
    #    if os.path.isdir(worldpop_popc_dir):
    #        files = sorted(os.listdir(worldpop_popc_dir))
    #        for f in files:
    #            s  = parameters.worldpop_popc.consume(os.path.join(worldpop_popc_dir, f))
    #            s['district'] = shape.split('_')[1]
    #            rows.append(s)
    #            print("\t{} - ".format(f) + str(s))
    #    else:
    #        print("no feature for {}".format(shape))
    #
    #df = pd.DataFrame(rows)
    #df.to_sql('worldpop_popc', engine)
