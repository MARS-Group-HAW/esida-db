import importlib
import datetime as dt
import sys
import os
import json

from esida import app, params, db, logger
from flask import render_template, make_response, abort, jsonify, request, redirect, url_for, send_from_directory
import markdown
from slugify import slugify

from dbconf import get_engine, close
from esida.models import Shape, Signal

import shapely
import pandas as pd
import numpy as np
import humanize


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



    return render_template('index.html',
        count_parameters = len(params),
        count_local_data_sources = len(newlist),
        total_size_human = humanize.naturalsize(total_size),
        sizes=newlist,
        sizes_json=json.dumps(newlist)
    )

@app.route("/regions")
def regions():
    shapes = Shape.query.where(Shape.type == "region").all()
    return render_template('regions.html', shapes=shapes)

@app.route("/districts")
def districts():
    shapes = Shape.query.where(Shape.type == "district").all()
    return render_template('districts.html', shapes=shapes)

@app.route("/map")
def map():
    regions = Shape.query.where(Shape.type == "region").all()
    districts = Shape.query.where(Shape.type == "district").all()

    engine = get_engine()
    meteostat=[]
    tza_hfr=[]
    tza_hfr_categories=[]

    with engine.connect() as con:

        meteo_tprecit_module = importlib.import_module('parameters.meteo_tprecit')
        meteo_tprecit = getattr(meteo_tprecit_module, 'meteo_tprecit')()
        if meteo_tprecit.is_loaded():
            rs = con.execute('SELECT id, meteostat_id, icao, wmo, name, ST_AsGeoJSON(geometry) AS geojson, (SELECT COUNT(*) FROM meteostat_daily WHERE meteostat_station_id = meteostat_stations.id) as count FROM meteostat_stations')
            for row in rs:
                meteostat.append(dict(row))

        thfr_disp_module = importlib.import_module('parameters.thfr_disp')
        thfr_disp = getattr(thfr_disp_module, 'thfr_disp')()
        if thfr_disp.is_loaded():
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

    parameters = []
    for p in params:
        pm = importlib.import_module('parameters.{}'.format(p))
        pc = getattr(pm, p)()
        if pc.is_loaded():
            parameters.append(pc)

    return render_template('shape.html',
        shape=shape,
        params=parameters
    )

@app.route('/shape/<int:shape_id>/<parameter_id>/<column>/json')
def download_json(shape_id, parameter_id, column):
    if parameter_id not in params:
        logger.warning("JSON Download for %s, but unknown parameter.", parameter_id)
        abort(500)

    pm = importlib.import_module(f'parameters.{parameter_id}')
    pc = getattr(pm, parameter_id)()

    if not pc.is_loaded():
        logger.warning("JSON Download for %s, but not loaded", parameter_id)
        abort(500)

    mean_for = request.args.get('mean_for')
    if mean_for:
        df = pc.mean(mean_for)
    else:
        df = pc.download(int(shape_id))

    if column not in df.columns:
        logger.warning("JSON Download for %s, but column %s not available.", parameter_id, column)
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

    df = df.sort_values(by=['year']).reset_index(drop=True)

    return df

def str2bool(v) -> bool:
    """ https://stackoverflow.com/a/715468/723769 """
    return str(v).lower() in ("yes", "true", "t", "1")

@app.route('/api/v1/shapes')
def api_shapes():

    if 'type' in request.args:
        shapes = Shape.query.where(Shape.type == request.args['type']).all()
    else:
        shapes = Shape.query.where().all()

    data = []

    for s in shapes:
        row = {
            'id': s.id,
            'name': s.name,
            'type': s.type,
            'area_sqm': s.area_sqm,
            'wkt': None
        }

        if 'wkt' in request.args and str2bool(request.args['wkt']):
            row['wkt'] = s.geom().wkt

        data.append(row)
    df = pd.DataFrame(data)

    return jsonify(
        data=df.to_dict('records')
    )

@app.route('/api/v1/shape/<int:shape_id>')
def api_data(shape_id):
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

    if 'format' in request.args and request.args['format'] == 'csv':
        filename=f"ESIDA_{shape.type}_{slugify(shape.name)}.csv"
        resp = make_response(df.to_csv(index=False))
        resp.headers["Content-Disposition"] = f"attachment; filename={filename}"
        resp.headers["Content-Type"] = "text/csv"
        return resp

    # the jsonify() method will not translate np.NaN to null for a valid JSON.
    # pandas' fillna() can't handle None, so we sett all "none"s to np.Nan and
    # make a replace to pythons None, which will wie translated by jsonify() to
    # JSONs null (https://stackoverflow.com/a/62691803/723769).
    # We can't use to_json() directly since we would get a string, and
    # than we would reply with a json String and not an object.
    return jsonify(
        data=df.fillna(np.nan).replace([np.nan], [None]).to_dict('records')
    )

@app.route('/api/v1/parameter/<string:parameter_id>')
def api_parameter(parameter_id):
    """ Get data and metadata for single parameter. """
    if parameter_id not in params:
        return jsonify(error="Parameter is not found"), 404

    pm = importlib.import_module(f'parameters.{parameter_id}')
    pc = getattr(pm, parameter_id)()

    if not pc.is_loaded():
        return jsonify(error="Parameter is not loaded"), 503

    start_date = request.args.get('start_date')
    if start_date:
        start_date = dt.datetime(year=int(start_date), month=1, day=1)

    end_date = request.args.get('end_date')
    if end_date:
        end_date = dt.datetime(year=int(end_date), month=1, day=1)

    df = pc.download(start=start_date, end=end_date)

    # in case wie have d date column (datetime obj) convert it to string.
    # the jsonify method would convert into an unlucky Date String like
    # `Mon, 01 Jan 2018 00:00:00 GMT`.
    if 'date' in df.columns:
        df['date'] = df['date'].apply(lambda x: x.strftime('%Y-%m-%d'))

    for x in  df.select_dtypes(include=['datetime64']).columns.tolist():
        df[x] = df[x].astype(str)

    shape_id = None

    data_quality = {
        'temporal_coverage': pc.da_temporal(shape_id=shape_id),
    }

    # the jsonify() method will not translate np.NaN to null for a valid JSON.
    # pandas' fillna() can't handle None, so we sett all "none"s to np.Nan and
    # make a replace to pythons None, which will wie translated by jsonify() to
    # JSONs null (https://stackoverflow.com/a/62691803/723769).
    # We can't use to_json() directly since we would get a string, and
    # than we would reply with a json String and not an object.
    return jsonify(
        data=df.fillna(np.nan).replace([np.nan], [None]).to_dict('records'),
        fields=pc.get_fields(),
        data_quality=data_quality
    )

@app.route('/api/v1/parameter_map/<string:parameter_id>/<string:shape_type>/<string:date>')
def api_parameter_map(parameter_id, shape_type, date):
    """ Get parameter values for given shape type and temporal point. """

    if parameter_id not in params:
        return jsonify(error="Parameter is not found"), 404

    if shape_type not in ['region', 'district']:
        return jsonify(error="Shape type invalid"), 404

    pm = importlib.import_module(f'parameters.{parameter_id}')
    pc = getattr(pm, parameter_id)()

    if not pc.is_loaded():
        return jsonify(error="Parameter is not loaded"), 503

    date_parts = date.split('-')
    if (len(date_parts) == 3):
        date_obj = dt.datetime(year=int(date_parts[0]), month=int(date_parts[1]), day=int(date_parts[2]))
    else:
        date_obj = dt.datetime(year=int(date), month=1, day=1)

    data = {
        'type': "FeatureCollection",
        "features":[]
    }

    rows = pc.get_map(shape_type, date_obj)
    min_value = sys.maxsize
    max_value = 0

    for r in rows:

        if r['value'] != None:
            min_value = min(r['value'], min_value)
            max_value = max(r['value'], max_value)

        f = {
            "type": "Feature",
            "properties": {
                "name":  r['name'],
                "value": r['value'],
            },
            "geometry": shapely.geometry.mapping(r['geometry']),
        }
        data['features'].append(f)

    return jsonify(geojson=data, min=min_value, max=max_value)

@app.route('/api/v1/da_spatial/<string:parameter_id>')
def api_da_spatial(parameter_id):
    """ Get data and metadata for single parameter. """
    if parameter_id not in params:
        return jsonify(error="Parameter is not found"), 404

    pm = importlib.import_module(f'parameters.{parameter_id}')
    pc = getattr(pm, parameter_id)()

    if not pc.is_loaded():
        return jsonify(error="Parameter is not loaded"), 503

    shape_id = None
    d = pc.da_spatial(shape_id=shape_id)
    data_quality = {
        'spatial_coverage': d[0]
    }

    # the jsonify() method will not translate np.NaN to null for a valid JSON.
    # pandas' fillna() can't handle None, so we sett all "none"s to np.Nan and
    # make a replace to pythons None, which will wie translated by jsonify() to
    # JSONs null (https://stackoverflow.com/a/62691803/723769).
    # We can't use to_json() directly since we would get a string, and
    # than we would reply with a json String and not an object.
    return jsonify(
        data=d[1],
        data_quality=data_quality
    )

@app.route('/api/v1/parameters')
def api_parameters():
    shape_id = request.args.get('shape_id')
    if shape_id and shape_id.isnumeric():
        shape_id = int(shape_id)
    else:
        shape_id = None

    rows = []
    spatial_details = []

    for p in params:
        pm = importlib.import_module(f'parameters.{p}')
        pc = getattr(pm, p)()


        spatial_coverage = None
        if request.args.get('da_spatial', type=bool):
            b = pc.da_spatial(shape_id=shape_id)
            if b:
                spatial_coverage = b[0]
                spatial_details += b[1]

        row = {
            'parameter_id': p,
            'timelines': pc.time_col,
            'loaded': pc.is_loaded(),
            'raw_data_size': pc.get_raw_data_size(),

            'temporal_expected': pc.da_temporal_expected(),
            'temporal_actual': pc.da_count_temporal(shape_id=shape_id),
            'temporal_coverage': pc.da_temporal(shape_id=shape_id),
            'temporal_first': pc.da_temporal_date_first(shape_id=shape_id),
            'temporal_last': pc.da_temporal_date_last(shape_id=shape_id),

            'spatial_coverage': spatial_coverage
        }

        rows.append(row)

    df = pd.DataFrame(rows)
    return jsonify(
        data=df.fillna(np.nan).replace([np.nan], [None]).to_dict('records'),
        spatial_details=spatial_details
    )

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

@app.route('/parameter-statistics')
def parameter_statistics():
    pars = []

    filters_str = request.args.get('filter_parameters')
    filters = None
    if filters_str:
        filters = request.args.get('filter_parameters').split(',')

    for p in params:

        if filters and p not in filters:
            continue

        pm = importlib.import_module('parameters.{}'.format(p))
        pc = getattr(pm, p)()

        if not pc.is_loaded():
            continue

        pars.append(pc)

    return render_template('parameter-statistics.html',
        parameters=pars,
        count=len(pars)
    )


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
        'class': getattr(pm, parameter_name)()
    }

    shapes = Shape.query.where().all()
    shapes_dropdown = {}

    for shape in shapes:
        if shape.type not in shapes_dropdown:
            shapes_dropdown[shape.type]  = []

        shapes_dropdown[shape.type].append({
            'name': shape.name,
            'id': shape.id
        })

    return render_template('parameter.html', parameter=parameter,
    shapes=shapes_dropdown)



@app.route("/download_parameter/<string:parameter_id>")
def download_parameter(parameter_id):

    if parameter_id not in params:
        abort(404)

    pm = importlib.import_module(f'parameters.{parameter_id}')
    pc = getattr(pm, parameter_id)()

    if not pc.is_loaded():
        df = pd.DataFrame([{'Parameter is not loaded': 1}])
    else:
        df = pc.download(shape_names=True)

    filename=f"ESIDA_{parameter_id}.csv"

    resp = make_response(df.to_csv(index=False))
    resp.headers["Content-Disposition"] = f"attachment; filename={filename}"
    resp.headers["Content-Type"] = "text/csv"

    return resp



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
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
