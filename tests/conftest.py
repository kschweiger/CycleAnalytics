import importlib.resources
import os
import tempfile

import pytest
from flask import Flask
from flask.testing import FlaskClient
from track_analyzer import ByteTrack, Track

from cycle_analytics import create_app
from cycle_analytics.database.creator import sync_categorical_values
from cycle_analytics.database.model import db as orm_db
from tests import resources
from tests.generate_data import create_test_data


@pytest.fixture(scope="session")
def app(
    fr_track: Track, fr_track_sub_segment: Track, fr_track_top_segment: Track
) -> Flask:
    app = create_app(
        {"FORCE_ENV_FOR_DYNACONF": "testing"},
        {"TESTING": True, "WTF_CSRF_ENABLED": False},
    )

    with app.app_context():
        orm_db.drop_all()
        orm_db.create_all()
        sync_categorical_values(orm_db)
        create_test_data(
            orm_db,
            {
                "fr_track": fr_track,
                "fr_track_sub_segment": fr_track_sub_segment,
                "fr_track_top_segment": fr_track_top_segment,
            },
        )

    return app


@pytest.fixture(scope="session")
def client(app: Flask) -> FlaskClient:
    return app.test_client()


@pytest.fixture(scope="session")
def sqlite_app() -> Flask:
    db_fd, db_path = tempfile.mkstemp()

    app = create_app(
        {"FORCE_ENV_FOR_DYNACONF": "testing"},
        {
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
            "database_schema": None,
        },
    )

    app.config["SERVER_NAME"] = "localhost"

    # with app.app_context():
    #     orm_db.drop_all()
    #     orm_db.create_all()
    #     create_test_data(orm_db)

    yield app

    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture(scope="session")
def sqlite_client(sqlite_app: Flask) -> FlaskClient:
    return sqlite_app.test_client()


@pytest.fixture(scope="session")
def fr_track() -> Track:
    resource_files = importlib.resources.files(resources)

    return ByteTrack(
        (resource_files / "Freiburger_Münster_nach_Schau_Ins_Land.gpx").read_bytes()
    )


@pytest.fixture(scope="session")
def fr_track_sub_segment() -> Track:
    resource_files = importlib.resources.files(resources)

    return ByteTrack((resource_files / "Teilstueck_Schau_ins_land.gpx").read_bytes())


@pytest.fixture(scope="session")
def fr_track_top_segment() -> Track:
    resource_files = importlib.resources.files(resources)

    return ByteTrack(
        (resource_files / "Oberer_teil_Schau_ins_land_enhanced.gpx").read_bytes()
    )
