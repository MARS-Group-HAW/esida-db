from flask import Flask
from flask import render_template, make_response, abort

from dbconf import get_engine, get_conn_string
import pandas as pd

import pkgutil
import importlib

import markdown

from slugify import slugify

app = Flask(__name__)
params  = [name for _, name, _ in pkgutil.iter_modules(['parameters'])]

@app.route("/")
def index():
    engine = get_engine()

    shapes=[]
    meteostat=[]
    with engine.connect() as con:
        rs = con.execute('SELECT gid, region_nam as region, newdist20 AS name, ST_AsGeoJSON(geom) AS geojson, ST_AsText(geom) as wkt FROM districts')
        for row in rs:
            shapes.append(dict(row))

    return render_template('table.html', shapes=shapes)

@app.route("/map")
def map():

    engine = get_engine()

    shapes=[]
    meteostat=[]
    with engine.connect() as con:
        rs = con.execute('SELECT gid, newdist20 AS name, ST_AsGeoJSON(geom) AS geojson FROM districts')
        for row in rs:
            shapes.append(dict(row))

        rs = con.execute('SELECT id, name, ST_AsGeoJSON(geometry) AS geojson, (SELECT COUNT(*) FROM meteostat_data WHERE meteostat_station_id = meteostat_stations.id) as count FROM meteostat_stations')
        for row in rs:
            meteostat.append(dict(row))

    return render_template('map.html', shapes=shapes, meteostat=meteostat)


@app.route("/shape/<int:shape_id>")
def shape(shape_id):
    engine = get_engine()

    shape=None
    with engine.connect() as con:
        # well this not good style...
        rs = con.execute('SELECT gid, newdist20 AS name, ST_AsGeoJSON(geom) AS geojson,  ST_AsText(geom) as wkt FROM districts WHERE gid={}'.format(int(shape_id)))
        shape = rs.fetchone()


    return render_template('shape.html', shape=shape)

@app.route('/shape/<int:shape_id>/parameters')
def download_csv(shape_id):
    engine = get_engine()

    shape=None
    with engine.connect() as con:
        # well this not good style...
        rs = con.execute('SELECT gid, newdist20 AS name, ST_AsGeoJSON(geom) AS geojson FROM districts WHERE gid={}'.format(int(shape_id)))
        shape = rs.fetchone()

    dfs = []

    for p in params:
        dfs.append(pd.read_sql_query('SELECT year, value as {} FROM {} WHERE district_id={}'.format(p, p, int(shape_id)), con=engine))


    df = dfs[0]
    for i in range(1, len(dfs)):
        df = df.merge(dfs[i], how='outer', on='year')

    df = df.sort_values(by=['year'])

    filename="esida_{}.csv".format(slugify(shape['name']))

    resp = make_response(df.to_csv(index=False))
    resp.headers["Content-Disposition"] = "attachment; filename={}".format(filename)
    resp.headers["Content-Type"] = "text/csv"
    return resp


@app.route('/parameter')
def parameters():
    parameters = []
    for p in params:
        pm = importlib.import_module('parameters.{}'.format(p))
        parameters.append({
            'name': pm.__name__.split('.')[1],
            'description': pm.__doc__,
        })

    return render_template('parameters.html', parameters=parameters)

@app.route('/')
@app.route("/parameter/<string:parameter_name>")
def parameter(parameter_name):

    if parameter_name not in params:
        abort(500)

    pm = importlib.import_module('parameters.{}'.format(parameter_name))
    parameter = {
        'name': pm.__name__.split('.')[1],
        'description': pm.__doc__,
        'description_html': markdown.markdown(pm.__doc__ or "*please add docstring to module*", extensions=['tables']),
    }

    return render_template('parameter.html', parameter=parameter)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
