from datetime import date, datetime, time, timedelta
from unittest.mock import MagicMock

import pytest
from flask import Flask
from flask.testing import FlaskClient
from gpxpy.gpx import GPXTrack
from pytest_mock import MockerFixture
from track_analyzer import PyTrack
from werkzeug.datastructures import MultiDict

from cycle_analytics.database.model import Bike, DatabaseTrack, Ride
from cycle_analytics.database.model import db as orm_db


@pytest.mark.parametrize(
    ("route", "exp_status_code"),
    [
        ("/", 200),
        ("/overview/", 200),
        ("/goals/", 200),
        ("/events/", 200),
        ("/segments/", 200),
        ("/settings/", 200),
    ],
)
def test_views_empty_database(
    sqlite_client: FlaskClient, route: str, exp_status_code: int
) -> None:
    response = sqlite_client.get(route)

    assert response.status_code == exp_status_code


@pytest.mark.parametrize(
    ("route", "exp_status_code"),
    [
        ("/", 200),
        ("/overview/", 200),
        ("/overview/journal", 200),
        ("/overview/heatmap", 200),
        ("/goals/", 200),
        ("/events/", 200),
        ("/add/ride", 200),
        ("/add/event", 200),
        ("/add/goal", 200),
        ("/segments/", 200),
        ("/segments/add", 200),
        ("/segments/show/6", 200),
        ("/add/bike", 200),
        # Track with Located events
        ("/ride/1/", 200),
        # No Track
        ("/ride/3/", 200),
        # Only elevation but not tiem
        ("/ride/5/", 200),
    ],
)
def test_views(client: FlaskClient, route: str, exp_status_code: int) -> None:
    response = client.get(route)

    assert response.status_code == exp_status_code


def test_add_bike(
    app: Flask,
    client: FlaskClient,
) -> None:
    this_year = datetime.now().year

    with app.app_context():
        bikes_pre = Bike.query.all()
        id_max_pre = max([b.id for b in bikes_pre])

    post_data = MultiDict(
        [
            ("name", "New Bike Name"),
            ("brand", "Some new brand"),
            ("model", "More detailed model name"),
            ("material", "1"),
            ("bike_type", "1"),
            ("bike_type_specification", "1"),
            ("weight", "12.2"),
            ("purchase", f"{this_year}-2-3"),
        ]
    )
    response = client.post(
        "/add/bike",
        data=post_data,
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        bikes_post = Bike.query.all()
        id_max_post = max([b.id for b in bikes_post])

        assert id_max_post > id_max_pre


@pytest.mark.parametrize(("is_enhanced", "exp_tracks"), [(True, 1), (False, 2)])
def test_enhance_track(
    mocker: MockerFixture,
    app: Flask,
    client: FlaskClient,
    is_enhanced: bool,
    exp_tracks: int,
) -> None:
    mock_enhancer = MagicMock()

    def update_elevation(track: GPXTrack, inplace: bool) -> None:
        assert len(track.segments) == 1
        for ptn in track.segments[0].points:
            ptn.elevation = ptn.elevation * 100

    mock_enhancer.enhance_track = update_elevation

    mocker.patch("cycle_analytics.utils.track.get_enhancer", return_value=mock_enhancer)

    this_year = datetime.now().year
    this_month = datetime.now().month
    track = PyTrack(
        points=[(10, 10), (10.001, 10.001), (10.002, 10.002)],
        elevations=[1, 2, 3],
        times=[
            datetime(this_year, this_month, 3, 13, 22),
            datetime(this_year, this_month, 3, 13, 22, 5),
            datetime(this_year, this_month, 3, 13, 22, 10),
        ],
    )
    with app.app_context():
        new_ride = Ride(
            ride_date=date(this_year, 2, 27),
            start_time=time(8, 8, 8),
            ride_duration=timedelta(seconds=60 * 20),
            total_duration=timedelta(seconds=(60 * 20) + 60),
            distance=1.234,
            id_terrain_type=2,
            id_bike=1,
        )

        new_ride.tracks.extend(
            [
                DatabaseTrack(
                    content=track.get_xml().encode(),
                    added=datetime(this_year, 2, 27, 18),
                    is_enhanced=is_enhanced,
                ),
            ]
        )

        orm_db.session.add(new_ride)
        orm_db.session.commit()

        pre_enhance_track_ids = [t.id for t in new_ride.tracks]

        response = client.get(f"/track/enhance/{new_ride.id}/")

        assert response.status_code == 302
        assert len(new_ride.tracks) == exp_tracks

        assert new_ride.tracks[-1].is_enhanced

        assert pre_enhance_track_ids != [t.id for t in new_ride.tracks]
