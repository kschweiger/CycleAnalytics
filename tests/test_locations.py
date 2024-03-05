import importlib.resources
from datetime import datetime

from flask import Flask
from flask.testing import FlaskClient
from geo_track_analyzer import ByteTrack
from sqlalchemy import select

from cycle_analytics.database.model import (
    DatabaseLocation,
    DatabaseTrack,
    TrackLocationAssociation,
)
from cycle_analytics.database.model import db as orm_db
from tests import resources


def test_match_locations_to_track(app: Flask, client: FlaskClient) -> None:
    with app.app_context():
        stmt = select(TrackLocationAssociation)
        track_locations_matches = orm_db.session.scalars(stmt).unique().all()
        assert len(track_locations_matches) == 0

    # NOTE: Track 3 should be from freiburg to Schauinsland from the
    # NOTE: Freiburger_Münster_nach_Schau_Ins_Land.gpx file
    response = client.get("/track/match_locations/3", follow_redirects=True)
    assert response.status_code == 200

    with app.app_context():
        stmt = select(TrackLocationAssociation)
        track_locations_matches = orm_db.session.scalars(stmt).unique().all()
        assert len(track_locations_matches) == 1


def test_remove_location(app: Flask, client: FlaskClient) -> None:
    resource_files = importlib.resources.files(resources)

    track = ByteTrack((resource_files / "Feldberg.gpx").read_bytes())
    lat, long = (47.8564519114077, 8.027996420860292)
    with app.app_context():
        db_track = DatabaseTrack(
            content=track.get_xml().encode(), added=datetime.now(), is_enhanced=False
        )
        db_location = DatabaseLocation(
            name="Feldberg location", latitude=lat, longitude=long
        )
        orm_db.session.add_all([db_track, db_location])
        orm_db.session.commit()
        track_id = db_track.id
        location_id = db_location.id

    response = client.get(f"/track/match_locations/{track_id}", follow_redirects=True)
    assert response.status_code == 200

    with app.app_context():
        track_locations_matches = (
            orm_db.session.scalars(
                select(TrackLocationAssociation)
                .filter(TrackLocationAssociation.track_id == track_id)
                .filter(TrackLocationAssociation.location_id == location_id)
            )
            .unique()
            .all()
        )
        assert len(track_locations_matches) == 1

    response = client.get(f"/locations/delete/{location_id}", follow_redirects=True)
    assert response.status_code == 200

    with app.app_context():
        location = orm_db.session.get(DatabaseLocation, location_id)
        assert location is None
        track_locations_matches = (
            orm_db.session.scalars(
                select(TrackLocationAssociation)
                .filter(TrackLocationAssociation.track_id == track_id)
                .filter(TrackLocationAssociation.location_id == track_id)
            )
            .unique()
            .all()
        )
        assert len(track_locations_matches) == 0
