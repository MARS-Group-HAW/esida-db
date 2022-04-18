import click

from esida import app, db

@app.cli.command("create-db")
def init_db():
    """ Create database tables for models (NOT parameter values! Those will be
    created individually by each parameter). """
    db.create_all()

@app.cli.command("drop-db")
def drop_db():
    """ Drop all model based tables. """
    db.drop_all()
