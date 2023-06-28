import os
import importlib
import datetime as dt

import yaml
import numpy as np
import pandas as pd
from flask import render_template, redirect, url_for, request

from esida import app, db
from esida.models import Signal
from dbconf import get_engine

@app.route('/signals')
def signal_index():
    signals = Signal.query.all()

    df = pd.read_sql("SELECT report_date, id, health_outcome FROM signal",  parse_dates=['report_date'], con=get_engine())

    dfx1 = df[df['health_outcome'].isin(['Suspected haemorrhagic fever', 'Suspected dengue haemorrhagic fever'])]
    dfx1 = dfx1.groupby([pd.Grouper(key='report_date', freq='W')]).count().reset_index()
    dfx1['x'] = dfx1['report_date'].astype(str)

    trace = [{
        'x': dfx1['x'].values.tolist(),
        'y': dfx1['id'].values.tolist(),
        'type': 'bar',
        'name': 'Suspected',
    }]

    return render_template('signal/index.html.jinja', signals=signals, trace=trace)

@app.route('/signal', methods = ['POST', 'GET'])
def signal_create():
    if request.method == 'POST':
        signal = Signal(
            report_date=dt.datetime.strptime(request.form['report_date'], '%Y-%m-%d').date(),
            health_outcome=request.form['health_outcome'],
            age=int(request.form['age']),
            sex=request.form['sex'],
            geometry='POINT({} {})'.format(request.form['lng'], request.form['lat'])
        )

        db.session.add(signal)
        db.session.commit()

        return redirect(url_for('signal_index'))

    return render_template('signal/create.html.jinja')

@app.route("/signal/<int:signal_id>")
def signal_show(signal_id):
    signal = Signal.query.get(signal_id)


    print(os.getcwd())
    with open("./input/algorithms/dengue-fever.yml", "r") as stream:
        try:
            algorithm = yaml.safe_load(stream)

            for key in algorithm['spec'].keys():
                algorithm['spec'][key]['key'] = key

        except yaml.YAMLError as exc:
            print(exc)

    results = {}

    # Process specs
    for shape in signal.shapes():
        spec = algorithm['spec'][algorithm['metadata']['start']]

        results[shape.id] = {
            'summary': None,
            'steps': []
        }

        while True:
            r = {
                'spec': spec,
                'ops': []
            }

            if 'end' in spec:
                #results[shape.id]['steps'].append(r)
                results[shape.id]['summary'] = spec
                break

            dl = spec['datalayer']
            pm = importlib.import_module(f'parameters.{dl}')
            pc = getattr(pm, dl)()

            booleans = []

            for op in spec['operators']:
                b, df = shape.op(signal, pc, op['op'], op['attrs'])
                booleans.append(b)
                r['ops'].append({
                    'op': op,
                    'result': b,
                    'data': df,
                    'data_v': df[spec['datalayer']].to_list()
                })

            positive = spec['positive']
            negative = spec['negative']

            if all(booleans):
                r['result'] = True
                spec = algorithm['spec'][positive]
            else:
                r['result'] = False
                spec = algorithm['spec'][negative]

            results[shape.id]['steps'].append(r)


    return render_template('signal/show.html.jinja',
        signal=signal,
        results=results
    )
