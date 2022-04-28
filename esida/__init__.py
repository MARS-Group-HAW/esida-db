import pkgutil
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash

from decouple import config
from dbconf import get_conn_string


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = get_conn_string()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


users = {
    config('FLASK_BASIC_AUTH_USERNAME', default='esida'): generate_password_hash(config('FLASK_BASIC_AUTH_PASSWORD', default='opendata22'))
}

db = SQLAlchemy(app)
auth = HTTPBasicAuth()

@auth.verify_password
def verify_password(username, password):
    if username in users and \
        check_password_hash(users.get(username), password):
        return username

if config('FLASK_BASIC_AUTH_FORCE', default=True, cast=bool):
    @app.before_request
    @auth.login_required
    def require_login():
        pass

params  = [name for _, name, _ in pkgutil.iter_modules(['parameters'])]

# import AFTER app, etc. has been declared!
import esida.models
import esida.views
import esida.cli

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
