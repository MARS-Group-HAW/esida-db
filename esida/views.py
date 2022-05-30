import importlib
import datetime as dt
import os

from esida import app, params, db
from flask import render_template, make_response, abort, request, redirect, url_for, send_from_directory
import markdown
from slugify import slugify

from dbconf import get_engine
from esida.models import Shape, Signal

import pandas as pd

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

        rs = con.execute('SELECT t."ID", t."Facility Name", t."Facility Type", t."Latitude", t."Longitude" FROM tza_hfr_healthfacilities t')
        for row in rs:
            tza_hfr.append(dict(row))

        rs = con.execute('SELECT t."Facility Type", COUNT(*) as count FROM tza_hfr_healthfacilities t WHERE t."Facility Type" IS NOT NULL GROUP BY t."Facility Type" ORDER BY count DESC;')
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

    # weather data
    engine = get_engine()


    chc_chirps = importlib.import_module('parameters.chc_chirps')

    chc_chirps_df = None
    if chc_chirps.is_loaded():
        chc_chirps_df = pd.read_sql_query('SELECT date, value FROM chc_chirps WHERE district_id={}'.format(int(shape_id)), con=engine)

    meteostat_df = pd.read_sql_query("SELECT * FROM meteostat_data WHERE meteostat_station_id = ( \
	SELECT id FROM meteostat_stations ORDER BY st_distance(ST_SetSRID(meteostat_stations.geometry, 4326), \
        ST_Centroid((SELECT geometry FROM district WHERE id = {})) ) ASC LIMIT 1) \
       ORDER BY time ASC ".format(int(shape_id)), con=engine)


    return render_template('shape.html', shape=shape, params=params,
        data=_get_parameters_for_district(shape_id),
        chc_chirps_df=chc_chirps_df, meteostat_df=meteostat_df)

def _get_parameters_for_shape(shape_id) -> pd.DataFrame:
    dfs = []

    for p in params:
        pm = importlib.import_module('parameters.{}'.format(p))

        rdf = pm.download(int(district_id), get_engine())
        if not rdf.empty:
            dfs.append(rdf)

    df = dfs[0]
    for i in range(1, len(dfs)):
        df = df.merge(dfs[i], how='outer', on='year')

    df = df.sort_values(by=['year']).reset_index()

    return df


@app.route('/shape/<int:shape_id>/parameters')
def download_csv(shape_id):
    engine = get_engine()

    shape=None
    with engine.connect() as con:
        # well this not good style...
        rs = con.execute('SELECT id, type, name FROM shape WHERE id={}'.format(int(shape_id)))
        shape = rs.fetchone()

    df = _get_parameters_for_shape(shape_id)

    filename="esida_{}_{}.csv".format(shape['type'], slugify(shape['name']))

    resp = make_response(df.to_csv(index=False))
    resp.headers["Content-Disposition"] = "attachment; filename={}".format(filename)
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
        })

    return render_template('parameters.html', parameters=pars)

@app.route("/parameter/<string:parameter_name>")
def parameter(parameter_name):

    if parameter_name not in params:
        abort(500)

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



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
