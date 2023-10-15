from data_organizer.db.connection import DatabaseConnection
from flask import Flask, current_app, g


def get_db() -> DatabaseConnection:
    if "db_connection" not in g:
        g.db_connection = DatabaseConnection(**current_app.config.db.to_dict())
    return g.db_connection


def close_db(e: None = None) -> None:
    db = g.pop("db_connection", None)

    if db is not None:
        db.close()


def init_app(app: Flask) -> None:
    app.teardown_appcontext(close_db)
