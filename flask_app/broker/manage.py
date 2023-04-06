"""Entrypoint for Specify Network Flask App."""

from flask.cli import FlaskGroup

from flask_app.broker import app

cli = FlaskGroup(app)

if __name__ == '__main__':
    cli()
