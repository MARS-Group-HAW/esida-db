from sqlalchemy.sql import func
from geoalchemy2.types import Geometry
from geoalchemy2.shape import to_shape

import shapely.geometry
import json
import humanize

from esida import app, db


class Shape(db.Model):
    """ Geometry for that parameters are aggregated, like Region/District.

    Self reference in SQL Alchemy: https://docs.sqlalchemy.org/en/14/orm/self_referential.html

    """

    id = db.Column(db.Integer, primary_key=True)

    parent_id = db.Column(db.Integer, db.ForeignKey('shape.id'))

    parent = db.relationship("Shape", remote_side=[id])
    children = db.relationship("Shape")

    name = db.Column(db.String(255), nullable=False)
    type = db.Column(db.String(255), nullable=False)

    region_code = db.Column(db.Integer, nullable=True, comment="Don't use PK, use id from shapefile to be in line with original data source")
    region_name = db.Column(db.String(255), nullable=True)
    district_c = db.Column(db.Integer, nullable=True, comment="Counter for districts within each region")

    geometry = db.Column(Geometry(srid=4326), nullable=False)
    area_sqm = db.Column(db.Float, nullable=True)

    def human_readable_area(self) -> str:
        if not self.area_sqm:
            return '-'
        return humanize.intcomma(round(self.area_sqm/1000000, 2))

    def geom(self):
        return to_shape(self.geometry)

    def geojson(self) -> str:
        return json.dumps(shapely.geometry.mapping(self.geom()))

class Signal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    edited_at = db.Column(db.DateTime(timezone=True), server_default=func.now())

    age = db.Column(db.Integer, nullable=False)
    report_date = db.Column(db.Date, nullable=False)
    sex = db.Column(db.String(255), nullable=False)
    geometry = db.Column(Geometry('POINT'), nullable=False)

    def point(self):
        return to_shape(self.geometry)
