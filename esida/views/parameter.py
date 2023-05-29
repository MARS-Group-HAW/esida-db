import importlib

from flask import render_template, abort, request

from esida import app, params, shape_types
from esida.models import Shape

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

    return render_template('parameter/index.html.jinja', parameters=pars)

@app.route("/parameter/<string:parameter_name>")
def parameter(parameter_name):

    if parameter_name not in params:
        abort(404)

    parameter_module = importlib.import_module(f'parameters.{parameter_name}')
    parameter_class  = getattr(parameter_module, parameter_name)()

    shapes = Shape.query.where().all()
    shapes_dropdown = {}
    for s in shapes:
        if s.type not in shapes_dropdown:
            shapes_dropdown[s.type]  = []
        shapes_dropdown[s.type].append({
            'name': s.name,
            'id':   s.id
        })

    return render_template('parameter/show.html.jinja',
        parameter=parameter_class,
        shapes=shapes_dropdown
    )
