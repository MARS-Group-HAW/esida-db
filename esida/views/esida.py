import importlib
import datetime as dt

import pandas as pd
from flask import render_template,request

from esida import app
from esida.models import Shape
from dbconf import get_engine

@app.route("/esida-risk")
def esida_risk_index():
    shapes = Shape.query.all()
    traces = {}

    dl_likelihood = importlib.import_module('parameters.esida_risk_likelihood')
    dl_likelihood = getattr(dl_likelihood, 'esida_risk_likelihood')()
    dl_impact = importlib.import_module('parameters.esida_risk_impact')
    dl_impact = getattr(dl_impact, 'esida_risk_impact')()

    if not (dl_likelihood.is_loaded & dl_impact.is_loaded):
        return render_template('custom/esida_risk/warning.html.jinja')

    whens = dl_impact.temporal_steps()
    when = request.args.get('when', None)
    if when:
        dp = when.split('-')
        if len(dp) == 3:
            when = dt.date(year=int(dp[0]), month=int(dp[1]), day=int(dp[2]))
        else:
            when = whens[-1]
    else:
        when = whens[-1]

    impact_df = dl_impact.download(when=when)
    likelihood_df = dl_likelihood.download(when=when)

    for s in shapes:
        shape_type = s.type

        #impact     = s.get('esida_risk_impact')['esida_risk_impact']
        #likelihood = s.get('esida_risk_likelihood')['esida_risk_likelihood']
        impact     = int(impact_df[(impact_df['shape_id'] == s.id)]['esida_risk_impact'].iloc[0])
        likelihood = int(likelihood_df[(likelihood_df['shape_id'] == s.id)]['esida_risk_likelihood'].iloc[0])
        label      = f"{s.name} {s.type}"

        if shape_type not in traces:
            traces[shape_type] = {
                'mode': 'markers+text',
                'type': 'scatter',
                'name': shape_type,
                'opacity': 1,
                'textposition': 'bottom center',

                'x': [],
                'y': [],
                'text': [],
                'marker': {
                    'size': 12
                }
            }

        traces[shape_type]['x'].append(likelihood)
        traces[shape_type]['y'].append(impact)
        traces[shape_type]['text'].append(label)

    return render_template('custom/esida_risk/index.html.jinja',
        shapes = shapes,
        dl_likelihood = dl_likelihood,
        dl_impact = dl_impact,
        traces=list(traces.values()),
        whens=whens,
        when=when
    )

@app.route("/esida-risk/<int:shape_id>")
def esida_risk_show(shape_id):

    dl_likelihood = importlib.import_module('parameters.esida_risk_likelihood')
    dl_likelihood = getattr(dl_likelihood, 'esida_risk_likelihood')()
    dl_impact = importlib.import_module('parameters.esida_risk_impact')
    dl_impact = getattr(dl_impact, 'esida_risk_impact')()

    if not (dl_likelihood.is_loaded & dl_impact.is_loaded):
        return render_template('custom/esida_risk/warning.html.jinja')

    shape = Shape.query.get(shape_id)

    # temporal
    likelihood_df = dl_likelihood.download(shape.id)
    #likelihood_df['date'] = likelihood_df['date'].dt.date
    likelihood_df['date'] = likelihood_df['date'].apply(lambda x: x.strftime('%Y-%m-%d'))

    impact_df = dl_impact.download(shape.id)
    impact_df['date'] = impact_df['date'].apply(lambda x: x.strftime('%Y-%m-%d'))

    traces_temporal = [{
        'x': list(likelihood_df['date'].tolist()),
        'y': list(likelihood_df['esida_risk_likelihood'].tolist()),
        'mode': 'lines+markers',
        'name': 'Likelihood',
        'line': {
            'shape': 'hv'
        },
    }, {
        'x': list(impact_df['date'].tolist()),
        'y': list(impact_df['esida_risk_impact'].tolist()),
        'mode': 'lines+markers',
        'name': 'Impact',
        'line': {
            'shape': 'hv'
        },
    }]

    shapes = Shape.query.where(Shape.type == shape.type).all()
    traces = {}

    whens = dl_impact.temporal_steps()
    when = request.args.get('when', None)
    if when:
        dp = when.split('-')
        if len(dp) == 3:
            when = dt.date(year=int(dp[0]), month=int(dp[1]), day=int(dp[2]))
        else:
            when = whens[-1]
    else:
        when = whens[-1]

    # create heatmap of all shapes in same category
    impact_df = dl_impact.download(when=when)
    likelihood_df = dl_likelihood.download(when=when)

    for s in shapes:
        shape_type = s.type
        impact     = float(impact_df[(impact_df['shape_id'] == s.id)]['esida_risk_impact'].iloc[0])
        likelihood = float(likelihood_df[(likelihood_df['shape_id'] == s.id)]['esida_risk_likelihood'].iloc[0])
        label      = f"{s.name} {s.type}"

        if shape_type not in traces:
            traces[shape_type] = {
                'mode': 'markers+text',
                'type': 'histogram2dcontour',
                'name': shape_type,
                'opacity': 1,
                'textposition': 'bottom center',

                'x': [],
                'y': [],
                'text': [],
                'marker': {
                    'size': 12
                }
            }

        traces[shape_type]['x'].append(likelihood)
        traces[shape_type]['y'].append(impact)
        traces[shape_type]['text'].append(label)

    # Put actual shape on heatmap
    traces['shape'] = {
        'mode': 'markers+text',
        'type': 'scatter',
        'name': shape.name,
        'opacity': 1,
        'textposition': 'bottom center',
        'x': [shape.get('esida_risk_likelihood', when=when)['esida_risk_likelihood']],
        'y': [shape.get('esida_risk_impact', when=when)['esida_risk_impact']],
        'text': [],
        'marker': {
            'color': 'black',
            'size': 12
        }
    }

    # explain likelihood
    log_likelihood_df = pd.read_sql('SELECT datalayer, current_score, threshold_score, value, actual_value FROM log_esida_risk_likelihood WHERE shape_id = %s AND "when" = %s ORDER BY index ASC',
                     con=get_engine(),
                     params=tuple([shape.id, when]))

    traces_likelihood = [{
        'x': list(log_likelihood_df['datalayer'].tolist()),
        'y': list(log_likelihood_df['current_score'].tolist()),
        'mode': 'lines+markers',
        'name': 'Score',
        'line': {
            'shape': 'hv'
        },
    }, {
        'x': list(log_likelihood_df['datalayer'].tolist()),
        'y': list(log_likelihood_df['threshold_score'].tolist()),
        'text': list(log_likelihood_df['threshold_score'].tolist()),
        'type': 'scatter',
        'name': 'Plus',
        'mode': 'markers+text',
        'textposition': 'top center',
        'line': {
            'shape': 'hv'
        },
    }]

    # explain impact
    log_impact_df = pd.read_sql('SELECT datalayer, current_score, threshold_score, value, actual_value FROM log_esida_risk_impact WHERE shape_id = %s AND "when" = %s ORDER BY index ASC',
                     con=get_engine(),
                     params=tuple([shape.id, when]));
    traces_impact = [{
        'x': list(log_impact_df['datalayer'].tolist()),
        'y': list(log_impact_df['current_score'].tolist()),
        'mode': 'lines+markers',
        'name': 'Score',
        'line': {
            'shape': 'hv'
        },
    }, {
        'x': list(log_impact_df['datalayer'].tolist()),
        'y': list(log_impact_df['threshold_score'].tolist()),
        'text': list(log_impact_df['threshold_score'].tolist()),
        'type': 'scatter',
        'name': 'Plus',
        'mode': 'markers+text',
        'textposition': 'top center',
        'line': {
            'shape': 'hv'
        },
    }]

    return render_template('custom/esida_risk/show.html.jinja',
                           dl_likelihood=dl_likelihood,
                           dl_impact = dl_impact,
                           traces_temporal=traces_temporal,
                           traces_likelihood=traces_likelihood,
                           log_likelihood_df=log_likelihood_df,
                           log_impact_df=log_impact_df,
                           traces_impact=traces_impact,
                           shape=shape,
                           whens=whens,
                           when=when,
                           traces=list(traces.values()))
