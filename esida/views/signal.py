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

    df = pd.read_sql('SELECT report_date, id FROM signal',  parse_dates=['report_date'], con=get_engine())

    dfx = df.groupby([pd.Grouper(key='report_date', freq='W')]).count()
    dfx['x'] = dfx.index.astype(np.int64) / int(1e6)
    dfx['x'] = dfx['x'].astype(int)
    dfx['y'] = dfx['id']
    data = dfx[['x', 'y']].values.tolist()

    return render_template('signal/index.html.jinja', signals=signals, data=data)

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
