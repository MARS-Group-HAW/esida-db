import importlib
import datetime as dt
import os
import json
from tracemalloc import start

from esida import app, params, db, logger
from flask import render_template, make_response, abort, jsonify, request, redirect, url_for, send_from_directory
import markdown
from slugify import slugify

from dbconf import get_engine, close
from esida.models import Shape, Signal

import pandas as pd
import numpy as np

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                          'images/favicon.ico',mimetype='image/vnd.microsoft.icon')

@app.route("/")
def index():
    return render_template('index.html')

@app.route("/regions")
def regions():
    regions = Shape.query.where(Shape.type == "region").all()
    return render_template('regions.html', shapes=regions)

@app.route("/districts")
def districts():
    districts = Shape.query.where(Shape.type == "district").all()
    return render_template('districts.html', shapes=districts)

@app.route("/map")
def map():

    regions = Shape.query.where(Shape.type == "region").all()
    districts = Shape.query.where(Shape.type == "district").all()

    engine = get_engine()
    meteostat=[]
    tza_hfr=[]
    tza_hfr_categories=[]
    with engine.connect() as con:
        rs = con.execute('SELECT id, meteostat_id, icao, wmo, name, ST_AsGeoJSON(geometry) AS geojson, (SELECT COUNT(*) FROM meteostat_data WHERE meteostat_station_id = meteostat_stations.id) as count FROM meteostat_stations')
        for row in rs:
            meteostat.append(dict(row))

        rs = con.execute('SELECT t."ID", t."Facility Name", t."Facility Type", t."Latitude", t."Longitude" FROM thfr t')
        for row in rs:
            tza_hfr.append(dict(row))

        rs = con.execute('SELECT t."Facility Type", COUNT(*) as count FROM thfr t WHERE t."Facility Type" IS NOT NULL GROUP BY t."Facility Type" ORDER BY count DESC;')
        for row in rs:
            tza_hfr_categories.append(dict(row))



    return render_template('map.html',
        regions=regions,
        districts=districts,
        meteostat=meteostat,
        tza_hfr=tza_hfr,
        tza_hfr_categories=tza_hfr_categories
    )


@app.route("/shape/<int:shape_id>")
def shape(shape_id):
    shape = Shape.query.get(shape_id)

    if shape is None:
        abort(404)

    # weather data
    engine = get_engine()


    # load chirps precipitation
    chirps_module = importlib.import_module('parameters.chirps_tprecit')
    chc_chirps = getattr(chirps_module, 'chirps_tprecit')()
    chc_chirps_data = []
    if chc_chirps.is_loaded():
        chc_chirps_df = pd.read_sql_query('SELECT date, chirps_tprecit FROM chirps_tprecit WHERE shape_id={}'.format(int(shape_id)), parse_dates=['date'], con=engine)
        chc_chirps_df['x'] = chc_chirps_df['date'].astype(np.int64) / int(1e6)
        chc_chirps_df['x'] = chc_chirps_df['x'].astype(int)
        chc_chirps_df['y'] = chc_chirps_df['chirps_tprecit']
        chc_chirps_data = chc_chirps_df[['x', 'y']].sort_values(by='x').to_json(orient="values")

    # nearest meteostat station to center of shape
    meteostat_station=None
    sql = "SELECT * FROM meteostat_stations ORDER BY st_distance( \
        ST_SetSRID(meteostat_stations.geometry, 4326), \
        ST_Centroid((SELECT geometry FROM shape WHERE id = {})) ) ASC LIMIT 1"
    with engine.connect() as con:
        rs = con.execute(sql.format(int(shape_id)))
        for row in rs:
            meteostat_station = dict(row)

    meteostat_df = pd.read_sql_query("SELECT * FROM meteostat_data WHERE meteostat_station_id = {} ORDER BY time ASC ".format(int(meteostat_station['id'])), parse_dates=['time'], con=engine)
    meteostat_df['x'] = meteostat_df['time'].astype(np.int64) / int(1e6)
    meteostat_df['x'] = meteostat_df['x'].astype(int)
    meteostat_df['y'] = meteostat_df['prcp']
    meteostat_df = meteostat_df[meteostat_df['y'].notna()]
    meteostat_data = meteostat_df[['x', 'y']].sort_values(by='x').to_json(orient="values")



    parameters = []
    for p in params:
        pm = importlib.import_module('parameters.{}'.format(p))
        pc = getattr(pm, p)()

        if pc.is_loaded():
            parameters.append(pc)

    return render_template('shape.html',
        shape=shape,
        params=parameters,
        meteostat_station=meteostat_station,
        chc_chirps_data=chc_chirps_data,
        meteostat_data=meteostat_data
    )

@app.route('/shape/<int:shape_id>/<parameter>/<column>/json')
def download_json(shape_id, parameter, column):
    if parameter not in params:
        logger.warning("JSON Download for %s, but unknown parameter.", parameter)
        abort(500)

    pm = importlib.import_module(f'parameters.{parameter}')
    pc = getattr(pm, parameter)()

    if not pc.is_loaded():
        logger.warning("JSON Download for %s, but not loaded", parameter)
        abort(500)

    df = pc.download(int(shape_id))
    if column not in df.columns:
        logger.warning("JSON Download for %s, but column %s not available.", parameter, column)
        abort(500)

    if 'year' in df.columns:
        df['date'] = df['year'].astype(str) + "-01-01"
        df['date'] = pd.to_datetime(df['date'])
    elif 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
    else:
        df['date'] = 0

    start_date = request.args.get('start_date')
    if start_date:
        start_date = dt.datetime(year=int(start_date), month=1, day=1)
        df = df[df['date'] >= start_date]

    end_date = request.args.get('end_date')
    if end_date:
        end_date = dt.datetime(year=int(end_date), month=1, day=1)
        df = df[df['date'] <= end_date]

    df = df.sort_values(by=['date']).reset_index()

    df['x'] = df['date'].astype(np.int64) / int(1e6)
    df['x'] = df['x'].astype(int)
    df['y'] = df[column]

    df = df[df['y'].notna()]

    return jsonify(
        data=df[['x', 'y']].values.tolist()
    )

def _get_parameters_for_shape(shape_id, filter_parameters=None, start_date=None, end_date=None) -> pd.DataFrame:
    dfs = []

    for p in params:
        if filter_parameters and p not in filter_parameters:
            continue

        pm = importlib.import_module(f'parameters.{p}')
        pc = getattr(pm, p)()

        rdf = pc.download(int(shape_id), start=start_date, end=end_date)
        if rdf.empty:
            continue

        # we merge data year column, so do not add it to the pool
        # if the column is missing
        if 'year' not in rdf:
            continue

        dfs.append(rdf)

    if len(dfs) == 0:
        return pd.DataFrame()

    if len(dfs) == 1:
        return dfs[0]

    df = dfs[0]
    for i in range(1, len(dfs)):
        df = df.merge(dfs[i], how='outer', on='year')

    df = df.sort_values(by=['year']).reset_index()

    return df

@app.route('/shape/<int:shape_id>/parameters')
def download_csv(shape_id):
    shape = Shape.query.get(shape_id)
    if shape is None:
        abort(404)

    filters_str = request.args.get('filter_parameters')
    filters = None
    if filters_str:
        filters = request.args.get('filter_parameters').split(',')

    start_date = request.args.get('start_date')
    if start_date:
        start_date = dt.datetime(year=int(start_date), month=1, day=1)

    end_date = request.args.get('end_date')
    if end_date:
        end_date = dt.datetime(year=int(end_date), month=1, day=1)

    df = _get_parameters_for_shape(shape_id,
        filter_parameters=filters,
        start_date=start_date,
        end_date=end_date)



    filename=f"ESIDA_{shape.type}_{slugify(shape.name)}.csv"

    resp = make_response(df.to_csv(index=False))
    resp.headers["Content-Disposition"] = f"attachment; filename={filename}"
    resp.headers["Content-Type"] = "text/csv"

    return resp


@app.route('/parameter')
def parameters():
    pars = []
    for p in params:
        pm = importlib.import_module('parameters.{}'.format(p))

        pars.append({
            'name': pm.__name__.split('.')[1],
            'description': pm.__doc__,
            'class': getattr(pm, p)()
        })

    return render_template('parameters.html', parameters=pars)

@app.route("/parameter/<string:parameter_name>")
def parameter(parameter_name):

    if parameter_name not in params:
        abort(404)

    pm = importlib.import_module(f'parameters.{parameter_name}')
    docblock = pm.__doc__ or "*please add docstring to module*"

    # check meta data directory
    docfile = f"input/meta_data/{parameter_name}.md"
    if os.path.isfile(docfile):
        with open(docfile) as f:
            docblock = f.read()

    docmd = markdown.markdown(docblock, extensions=['tables'])
    docmd = docmd.replace('<table>', '<table class="table table-sm table-meta_data">')

    parameter = {
        'name': pm.__name__.split('.')[1],
        'description': pm.__doc__,
        'description_html': docmd,
    }

    return render_template('parameter.html', parameter=parameter)

@app.route('/signals')
def signals():
    signals = Signal.query.all()
    return render_template('signal/index.html', signals=signals)

@app.route('/signal', methods = ['POST', 'GET'])
def signal():
    if request.method == 'POST':

        signal = Signal(age=int(request.form['age']),
            report_date=dt.datetime.strptime(request.form['report_date'], '%Y-%m-%d').date(),
            sex=request.form['sex'],
            geometry='POINT({} {})'.format(request.form['lng'], request.form['lat'])
        )

        db.session.add(signal)
        db.session.commit()

        return redirect(url_for('signals'))

    return render_template('signal/create.html')


@app.after_request
def after_request_callback(response):
    close()
    return response


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
