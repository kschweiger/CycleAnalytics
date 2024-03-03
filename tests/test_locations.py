from flask import Flask
from flask.testing import FlaskClient
from sqlalchemy import select

from cycle_analytics.database.model import TrackLocationAssociation
from cycle_analytics.database.model import db as orm_db


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
