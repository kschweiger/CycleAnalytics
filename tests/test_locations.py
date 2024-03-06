import importlib.resources
from datetime import datetime

import pytest
from flask import Flask
from flask.testing import FlaskClient
from geo_track_analyzer import ByteTrack
from sqlalchemy import select

from cycle_analytics.database.converter import initialize_overviews
from cycle_analytics.database.model import (
    DatabaseLocation,
    DatabaseTrack,
    TrackLocationAssociation,
)
from cycle_analytics.database.model import db as orm_db
from tests import resources


@pytest.mark.dependency()
def test_match_locations_to_track(app: Flask, client: FlaskClient) -> None:
    with app.app_context():
        stmt = select(TrackLocationAssociation)
        track_locations_matches = orm_db.session.scalars(stmt).unique().all()
        assert len(track_locations_matches) == 0

    # NOTE: Track 2 should be from freiburg to Schauinsland from the
    # NOTE: Freiburger_Münster_nach_Schau_Ins_Land.gpx file
    response = client.get("/track/match_locations/2", follow_redirects=True)
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


def test_match_tracks(app: Flask, client: FlaskClient) -> None:
    resource_files = importlib.resources.files(resources)

    track_1 = ByteTrack((resource_files / "Loretto_Route_1.gpx").read_bytes())
    track_2 = ByteTrack((resource_files / "Loretto_Route_2.gpx").read_bytes())

    overview_1 = initialize_overviews(track_1)
    overview_2 = initialize_overviews(track_2)

    for attr in [
        "max_velocity",
        "max_velocity_kmh",
        "avg_velocity",
        "avg_velocity_kmh",
    ]:
        setattr(overview_1[0], attr, 10)
        setattr(overview_2[0], attr, 10)

    lat, long = (47.98384596643959, 7.8409284353256234)

    with app.app_context():
        db_track_1 = DatabaseTrack(
            content=track_1.get_xml().encode(),
            added=datetime.now(),
            is_enhanced=False,
            overviews=overview_1,
        )
        db_track_2 = DatabaseTrack(
            content=track_2.get_xml().encode(),
            added=datetime.now(),
            is_enhanced=False,
            overviews=overview_2,
        )
        db_location = DatabaseLocation(name="Loretto KH", latitude=lat, longitude=long)
        orm_db.session.add_all([db_track_1, db_track_2, db_location])
        orm_db.session.commit()
        track_1_id = db_track_1.id
        track_2_id = db_track_2.id
        location_id = db_location.id

    response = client.get(
        f"/locations/match_tracks/{location_id}", follow_redirects=True
    )
    assert response.status_code == 200

    with app.app_context():
        stmt = select(TrackLocationAssociation).filter(
            TrackLocationAssociation.location_id == location_id
        )
        track_locations_matches = orm_db.session.scalars(stmt).unique().all()
        assert len(track_locations_matches) == 2
        matching_tracks = [_match.track_id for _match in track_locations_matches]
        assert track_1_id in matching_tracks
        assert track_2_id in matching_tracks


# NOTE: Run the matching from `test_match_locations_to_track` again to test
# NOTE: if it does not try to insert the TrackLocationAssociation again.
@pytest.mark.dependency(depends=["test_match_locations_to_track"])
def test_match_tracks_skip(app: Flask, client: FlaskClient) -> None:
    with app.app_context():
        stmt = select(TrackLocationAssociation).filter(
            TrackLocationAssociation.track_id == 2
        )
        track_locations_matches = orm_db.session.scalars(stmt).unique().all()
        assert len(track_locations_matches) == 1
        location_id = track_locations_matches[0].location_id

    response = client.get(
        f"/locations/match_tracks/{location_id}", follow_redirects=True
    )
    assert response.status_code == 200
