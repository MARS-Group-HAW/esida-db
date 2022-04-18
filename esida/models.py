from sqlalchemy.sql import func
from geoalchemy2.types import Geometry
from geoalchemy2.shape import to_shape

from esida import app, db


class Region(db.Model):
    """ Organizational unit in tanzania, contains multiple districts. """
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(255), nullable=False)
    region_id = db.Column(db.Integer, nullable=False, unique=True)
    geometry = db.Column(Geometry(srid=4326), nullable=False)

    districts = db.relationship('District', backref='district', lazy=True)

    def geom(self):
        return to_shape(self.geometry)


class District(db.Model):
    """ Organizational unit in tanzania, belongs to one region. """
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(255), nullable=False)

    region_id = db.Column(db.Integer, db.ForeignKey('region.region_id'), nullable=False, comment="Don't use PK, use id from shapefile to be in line with original data source")
    region_name = db.Column(db.String(255), nullable=False)
    district_c = db.Column(db.Integer, nullable=False, comment="Counter for districts within each region")

    geometry = db.Column(Geometry(srid=4326), nullable=False)

    def geom(self):
        return to_shape(self.geometry)


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

