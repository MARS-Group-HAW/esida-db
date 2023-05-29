import os
import importlib

import json
import humanize
from flask import render_template, send_from_directory

from esida import app, params

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                          'images/favicon.ico',mimetype='image/vnd.microsoft.icon')

@app.route("/")
def index():

    sizes = {}
    total_size = 0
    for p in params:
        pm = importlib.import_module(f'parameters.{p}')
        pc = getattr(pm, p)()

        base = pc.get_data_path().name

        if base not in sizes:
            size_in_bytes = pc.get_raw_data_size()
            total_size += size_in_bytes
            sizes[base] = {
                'name': base,
                'y': size_in_bytes,
                'human': humanize.naturalsize(size_in_bytes),
                'parameter_ids': [pc.parameter_id]
            }
        else:
            sizes[base]['parameter_ids'].append(pc.parameter_id)

    newlist = sorted(list(sizes.values()), key=lambda d: d['y'], reverse=True)

    return render_template('index.html.jinja',
        count_parameters = len(params),
        count_local_data_sources = len(newlist),
        total_size_human = humanize.naturalsize(total_size),
        sizes=newlist,
        sizes_json=json.dumps(newlist)
    )

@app.route("/map")
def map():
    parameters = []
    for p in params:
        pm = importlib.import_module('parameters.{}'.format(p))
        pc = getattr(pm, p)()
        if pc.is_loaded and pc.has_raw_data():
            parameters.append(pc)

    return render_template('map.html.jinja',
        parameters=parameters
    )
