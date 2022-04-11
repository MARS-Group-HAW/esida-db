# db.py
# provides a connect() function that returns a SQLAlchemy connection to the database passed to config(); sample uses config() defaults.

from sqlalchemy import create_engine
from config import config

def get_conn_string():
    try:
        # read connection params
        params = config()
        return f"postgresql://{params['username']}:{params['password']}@{params['hostname']}:{params['port']}/{params['database']}"
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

    try:
        # read connection params
        params = config()

        # connect to PostgreSQL server
        engine = create_engine(conn_string)

        connection = engine.connect()

        return connection
    except:
        return print("Connection failed.")

# for debug
if __name__ == '__main__':
    connection = connect()
    result = connection.execute("select version();")
    for row in result:
        print(row)
    connection.close()
