import pkgutil
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
from slugify import slugify

from decouple import config
from dbconf import get_conn_string
import log

from .version import __version__

logger = log.setup_custom_logger('root')
app = Flask(__name__)

# deployed app would often show an "sqlalchemy.exc.OperationalError:
#   (psycopg2.OperationalError) server closed the connection unexpectedly"
# exception on first request. This seems to be related to the connection
# going idle. With the pool_pre_ping setting a simple SELECT 1; query is
# used to test if the connection is still available for each new session.
# see: https://stackoverflow.com/q/55457069/723769,
# https://docs.sqlalchemy.org/en/14/core/pooling.html#pool-disconnects-pessimistic
# https://github.com/pallets-eco/flask-sqlalchemy/issues/589
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {"pool_pre_ping": True}
app.config['SQLALCHEMY_DATABASE_URI'] = get_conn_string()

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

users = {
    config('FLASK_BASIC_AUTH_USERNAME', default='esida'): generate_password_hash(config('FLASK_BASIC_AUTH_PASSWORD', default='opendata22'))
}

db = SQLAlchemy(app)
auth = HTTPBasicAuth()

@auth.verify_password
def verify_password(username, password):
    """ Verify given password with known users. """
    if username in users and \
        check_password_hash(users.get(username), password):
        return username

if config('FLASK_BASIC_AUTH_FORCE', default=True, cast=bool):
    @app.before_request
    @auth.login_required
    def require_login():
        """ this is a callback before ALL routes. by annotating it with
        login_required we force ALL routes to be authenticated. """
        pass

params  = [name for _, name, _ in pkgutil.iter_modules(['parameters'])]

def shape_types() -> list:
    """ Return available shape types for hierarchical area of interests. """
    types = config('DATAHUB_SHAPE_TYPES', default="region district", cast=str)
    return types.split(" ")


@app.context_processor
def inject_shape_types():
    """ Inject shape_types from .env file into ALL view templates. """
    return dict(shape_types=shape_types(), version=__version__)


@app.template_filter('slugify')
def _slugify(string):
    if not string:
        return ""
    return slugify(string)



# import AFTER app, etc. has been declared!
import esida.models
import esida.views
import esida.cli

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
