import importlib

from flask import render_template, abort, request

from esida import app, params, shape_types
from esida.models import Shape

@app.route("/shapes/<string:shape_type>")
def shape_index(shape_type):
    """ View for all shapes of a given type. """
    if shape_type not in shape_types():
        abort(404)

    shapes = Shape.query.where(Shape.type == shape_type).order_by(Shape.name.asc()).all()
    return render_template('shape/index.html.jinja', shape_type=shape_type, shapes=shapes)

@app.route("/shape/<int:shape_id>")
def shape_show(shape_id):
    """ View for single shape identified by it's ID. """
    shape = Shape.query.get(shape_id)

    if shape is None:
        abort(404)

    parameters = []
    for p in params:
        pm = importlib.import_module(f'parameters.{p}')
        pc = getattr(pm, p)()
        if pc.is_loaded:
            parameters.append(pc)

    return render_template('shape/show.html.jinja',
        shape=shape,
        params=parameters
    )
