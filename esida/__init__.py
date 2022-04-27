import pkgutil
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_basicauth import BasicAuth

from decouple import config
from dbconf import get_conn_string


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = get_conn_string()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['BASIC_AUTH_USERNAME'] = config('FLASK_BASIC_AUTH_USERNAME', default='esida')
app.config['BASIC_AUTH_PASSWORD'] = config('FLASK_BASIC_AUTH_FORCE', default='opendata22')
app.config['BASIC_AUTH_FORCE'] = config('FLASK_BASIC_AUTH_FORCE', default=True, cast=bool)


db = SQLAlchemy(app)
basic_auth = BasicAuth(app)

params  = [name for _, name, _ in pkgutil.iter_modules(['parameters'])]

# import AFTER app, etc. has been declared!
import esida.models
import esida.views
import esida.cli

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
