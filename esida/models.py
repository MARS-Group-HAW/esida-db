import importlib
import importlib.util

from sqlalchemy.sql import func, text
from sqlalchemy.orm import deferred
from geoalchemy2.types import Geometry
from geoalchemy2.shape import to_shape

import shapely.geometry
import json
import humanize

import datetime as dt

from esida import app, db


class Shape(db.Model):
    """ Geometry for that parameters are aggregated, like Region/District.

    Self reference in SQL Alchemy: https://docs.sqlalchemy.org/en/14/orm/self_referential.html

    """

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    type = db.Column(db.String(255), nullable=False)

    parent_id = db.Column(db.Integer, db.ForeignKey('shape.id'))

    area_sqm = db.Column(db.Float, nullable=True)
    properties = db.Column(db.JSON, nullable=True)

    geometry = deferred(db.Column(Geometry(srid=4326), nullable=False))

    parent = db.relationship("Shape", remote_side=[id], viewonly=True)
    children = db.relationship("Shape", order_by="asc(Shape.name)", viewonly=True)

    def human_readable_area(self) -> str:
        if not self.area_sqm:
            return '-'
        return humanize.intcomma(round(self.area_sqm/1000000, 2))

    def geom(self):
        return to_shape(self.geometry)

    def geojson(self) -> str:
        return json.dumps({
            "type": "Feature",
            'geometry': shapely.geometry.mapping(self.geom()),
            'properties': {
                'id': self.id,
                'name': self.name,
            }
        })

    def op(self, signal, dl, op, params) -> bool:
        """ checks if operator is defined for given data layer and if so
        calls it. """
        op_func = getattr(dl, f"op_{op}", None)
        if not callable(op_func):
            raise Exception(f"{op} is not available for {dl.parameter_id}")

        return op_func(signal, self.id, **params)

    def get(self, dl, fallback_parent=False, when=None, retry=False, obj=False):
        """ Gets the latest known value for the given data layer on this shape. """

        if isinstance(dl, str):
            pm = importlib.import_module(f'parameters.{dl}')
            dl = getattr(pm, dl)()

        value = dl.peek(self.id, when=when, retry=retry)

        if value is None and fallback_parent and self.parent is not None:
            value = self.parent.get(dl, fallback_parent, when=when, retry=retry)

            if value:
               value[f"{dl.parameter_id}_inferred"] = True

        if obj:
            return DatalayerPeek(dl, value)

        return value


class DatalayerPeek():

    def __init__(self, dl, peek) -> None:
        self.dl = dl
        self.peek = peek

    def has_value(self):
        return self.peek is not None

    def is_inferred(self) -> bool:
        return self.peek and f"{self.dl.parameter_id}_inferred" in self.peek

    def get_shape(self) -> Shape:
        return Shape.query.get(self.peek['shape_id'])

    def get_value(self):
        return self.peek and self.peek[self.dl.parameter_id]

    def get_time_col(self):
        return self.peek and self.peek[self.dl.time_col]

    def get_color(self):
        if self.is_inferred():

            colors = {
                'region': '#FCE1C6',
                'country': '#FFC7CE',
            }

            return colors[self.get_shape().type]

        return None

class Signal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    edited_at = db.Column(db.DateTime(timezone=True), server_default=func.now())

    report_date = db.Column(db.Date, nullable=False)
    health_outcome = db.Column(db.String(255), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    sex = db.Column(db.String(255), nullable=False)
    geometry = db.Column(Geometry('POINT', srid=4326), nullable=False)

    def point(self):
        return to_shape(self.geometry)

    def shapes(self):
        """ Finds shapes that intersect with this signal. """
        stmt = text('ST_Contains(geometry, (SELECT geometry FROM signal WHERE id = :id))')
        stmt = stmt.bindparams(id=self.id)
        shapes = Shape.query.where(stmt).all()
        return shapes

    def report_date_ts(self) -> int:
        return int(self.report_date.replace(tzinfo=dt.timezone.utc).timestamp()) * 1000
