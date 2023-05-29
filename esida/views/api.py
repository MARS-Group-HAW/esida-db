import sys
import time
import zipfile
import importlib
import datetime as dt
from io import BytesIO

import shapely
import numpy as np
import pandas as pd
from slugify import slugify
from sqlalchemy.orm import undefer
from flask import render_template, make_response, abort, jsonify, send_file, request, url_for

from esida.models import Shape
from esida import app, params, db, logger, shape_types

@app.route('/shape/<int:shape_id>/<parameter_id>/<column>/json')
def download_json(shape_id, parameter_id, column):
    if parameter_id not in params:
        logger.warning("JSON Download for %s, but unknown parameter.", parameter_id)
        abort(500)

    pm = importlib.import_module(f'parameters.{parameter_id}')
    pc = getattr(pm, parameter_id)()

    if not pc.is_loaded:
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


def str2bool(v) -> bool:
    """ https://stackoverflow.com/a/715468/723769 """
    return str(v).lower() in ("yes", "true", "t", "1")

def _get_parameters_for_shape(shape_id, filter_parameters=None, start_date=None, end_date=None, join_col='year') -> pd.DataFrame:
    dfs = []

    for p in params:
        if filter_parameters and p not in filter_parameters:
            continue

        pm = importlib.import_module(f'parameters.{p}')
        pc = getattr(pm, p)()

        if pc.time_col is not join_col:
            continue

        rdf = pc.download(int(shape_id), start=start_date, end=end_date, select_shape_name=False)

        if rdf.empty:
            continue

        # we merge data year column, so do not add it to the pool
        # if the column is missing
        if join_col not in rdf:
            continue

        dfs.append(rdf)

    if len(dfs) == 0:
        return pd.DataFrame()

    if len(dfs) == 1:
        return dfs[0]

    df = dfs[0]
    for i in range(1, len(dfs)):
        df = df.merge(dfs[i], how='outer', on=join_col)

    df = df.sort_values(by=[join_col]).reset_index(drop=True)

    return df

@app.route('/api/v1/shapes')
def api_shapes():

    output_format = 'csv'
    if 'format' in request.args:
        output_format = request.args['format']

    if 'shape_id' in request.args:
        shapes = [Shape.query.options(undefer("geometry")).get(request.args['shape_id'])]
    elif 'type' in request.args:
        shapes = Shape.query.where(Shape.type == request.args['type']).options(undefer("geometry")).all()
    else:
        shapes = Shape.query.options(undefer("geometry")).all()

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


    if output_format == 'json':
        data = {
            'type': "FeatureCollection",
            "features":[]
        }

        for s in shapes:
            f = {
                "type": "Feature",
                "properties": {
                    "name":  s.name,
                    'type': s.type,
                    "shape_id": s.id,
                    "url": url_for('shape_show', shape_id=s.id)
                },
                "geometry": shapely.geometry.mapping(s.geom()),
            }
            data['features'].append(f)
        return jsonify(data)

    if output_format == 'wkt':
        wkts = ""
        for s in shapes:
            wkts += s.geom().wkt + "\n"

        response = make_response(wkts, 200)
        response.mimetype = "text/plain"
        return response

    df = pd.DataFrame(data)

    resp = make_response(df.to_csv(index=False))
    resp.headers["Content-Type"] = "text/csv"
    return resp





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

    if not pc.is_loaded:
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

    if shape_type not in shape_types():
        return jsonify(error="Shape type invalid"), 404

    pm = importlib.import_module(f'parameters.{parameter_id}')
    pc = getattr(pm, parameter_id)()

    if not pc.is_loaded:
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

    if len(rows) == 0:
        return jsonify(error="No data found for this shape type."), 503

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



@app.route('/api/v1/parameter_data_map/<string:parameter_id>/<string:date>')
def api_parameter_data_map(parameter_id, date):
    """ Fetch the raw data for a layer. """

    if parameter_id not in params:
        return jsonify(error="Parameter is not found"), 404

    pm = importlib.import_module(f'parameters.{parameter_id}')
    pc = getattr(pm, parameter_id)()

    if not pc.is_loaded:
        return jsonify(error="Parameter is not loaded"), 503

    date_parts = date.split('-')
    if (len(date_parts) == 3):
        date_obj = dt.datetime(year=int(date_parts[0]), month=int(date_parts[1]), day=int(date_parts[2]))
    else:
        date_obj = dt.datetime(year=int(date), month=1, day=1)

    data = pc.data_map()

    return jsonify(geojson=data)

    response = app.response_class(
        response=json,
        status=200,
        mimetype='application/json'
    )
    return response


@app.route('/api/v1/da_spatial/<string:parameter_id>')
def api_da_spatial(parameter_id):
    """ Get data and metadata for single parameter. """
    if parameter_id not in params:
        return jsonify(error="Parameter is not found"), 404

    pm = importlib.import_module(f'parameters.{parameter_id}')
    pc = getattr(pm, parameter_id)()

    if not pc.is_loaded:
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
            'category': pc.get_category(),
            'title': pc.get_title(),
            'timelines': pc.time_col,
            'loaded': pc.is_loaded,
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


    if request.args.get('format', None) == 'csv':

        filename = f"ESIDA_parameters.csv"

        resp = make_response(df.to_csv(index=False))
        resp.headers["Content-Disposition"] = f"attachment; filename={filename}"
        resp.headers["Content-Type"] = "text/csv"
        return resp




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

    df_year = _get_parameters_for_shape(shape_id,
        filter_parameters=filters,
        start_date=start_date,
        end_date=end_date,
        join_col='year')

    df_date = _get_parameters_for_shape(shape_id,
        filter_parameters=filters,
        start_date=start_date,
        end_date=end_date,
        join_col='date')

    # we have results on both potential time resolutions, create .zip file
    # download for both!
    if len(df_year) > 0 and len(df_date) > 0:
        files = [{
            'name': f"ESIDA_{shape.type}_{slugify(shape.name)}_year.csv",
            'content': df_year.to_csv(index=False)
        }, {
            'name': f"ESIDA_{shape.type}_{slugify(shape.name)}_date.csv",
            'content': df_date.to_csv(index=False)
        } ]

        memory_file = BytesIO()
        with zipfile.ZipFile(memory_file, 'w') as zf:
            for file in files:
                data = zipfile.ZipInfo(file['name'])
                data.date_time = time.localtime(time.time())[:6]
                data.compress_type = zipfile.ZIP_DEFLATED
                zf.writestr(data, file['content'])
        memory_file.seek(0)

        return send_file(memory_file, attachment_filename=f"ESIDA_{shape.type}_{slugify(shape.name)}.zip", as_attachment=True)

    # only date or year are available for the query, only send the available
    # resolution directly as .csv, no need to zip a single file.
    df = df_year
    temporal_resolution = 'year'
    if len(df) == 0:
        temporal_resolution = 'date'
        df = df_date

    filename=f"ESIDA_{shape.type}_{slugify(shape.name)}_{temporal_resolution}.csv"

    resp = make_response(df.to_csv(index=False))
    resp.headers["Content-Disposition"] = f"attachment; filename={filename}"
    resp.headers["Content-Type"] = "text/csv"
    return resp





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

        if not pc.is_loaded:
            continue

        pars.append(pc)

    return render_template('parameter/temporal-statistics.html.jinja',
        parameters=pars,
        count=len(pars)
    )

@app.route("/download_parameter/<string:parameter_id>")
def download_parameter(parameter_id):

    if parameter_id not in params:
        abort(404)

    pm = importlib.import_module(f'parameters.{parameter_id}')
    pc = getattr(pm, parameter_id)()

    shape_type = request.args.get('shape_type', None)

    if not pc.is_loaded:
        df = pd.DataFrame([{'Parameter is not loaded': 1}])
    else:
        df = pc.download(shape_type=shape_type)

    if request.args.get('format', None) == 'excel':
        filename=f"ESIDA_{parameter_id}.xlsx"

        with BytesIO() as b:
            writer = pd.ExcelWriter(b, engine='openpyxl')
            df.to_excel(writer, index=False, freeze_panes=(1, 1))
            writer.close()
            resp = make_response(b.getvalue())
            resp.headers["Content-Disposition"] = f"attachment; filename={filename}"
            resp.headers["Content-Type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        filename=f"ESIDA_{parameter_id}.csv"
        resp = make_response(df.to_csv(index=False))
        resp.headers["Content-Disposition"] = f"attachment; filename={filename}"
        resp.headers["Content-Type"] = "text/csv"

    return resp
