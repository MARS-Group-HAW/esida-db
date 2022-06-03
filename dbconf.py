# db.py
# provides a connect() function that returns a SQLAlchemy connection to the database passed to config(); sample uses config() defaults.

from sqlalchemy import create_engine
from decouple import config

_connection = None

def get_conn_string():
    try:
        # read connection params
        return f"postgresql://{config('POSTGIS_USER')}:{config('POSTGIS_PASS')}@{config('POSTGIS_HOST')}:{config('POSTGIS_PORT')}/{config('POSTGIS_DB')}"
    except:
        return print("Could not build connection string.")

def get_engine():
    """ Create engine to the PostgreSQL database server """

    try:
        # connect to PostgreSQL server
        engine = create_engine(get_conn_string())

        return engine
    except:
        return print("Connection failed.")


def connect():
    """ Connect to the PostgreSQL database server """

    global _connection

    if _connection is not None:
        return _connection

    try:
        # connect to PostgreSQL server
        engine = get_engine()

        _connection = engine.connect()

        return _connection
    except:
        return print("Connection failed.")

def close():
    global _connection

    if _connection is not None:
        _connection.close()
        _connection = None

# for debug
if __name__ == '__main__':
    connection = connect()
    result = connection.execute("select version();")
    for row in result:
        print(row)
    connection.close()
