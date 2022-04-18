import pkgutil
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from dbconf import get_conn_string


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = get_conn_string()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
params  = [name for _, name, _ in pkgutil.iter_modules(['parameters'])]

# import AFTER app, etc. has been declared!
import esida.models
import esida.views
import esida.cli

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
