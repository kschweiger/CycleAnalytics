import uuid
from datetime import date, datetime, time, timedelta
from typing import Any
from unittest.mock import MagicMock

import pytest
from flask import Flask
from flask.testing import FlaskClient
from geo_track_analyzer import PyTrack
from gpxpy.gpx import GPXTrack
from pytest_mock import MockerFixture
from werkzeug.datastructures import MultiDict

from cycle_analytics.database.model import Bike, DatabaseSegment, DatabaseTrack, Ride
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
        ("ride/add_note/1", 200),
    ],
)
def test_views(client: FlaskClient, route: str, exp_status_code: int) -> None:
    response = client.get(route)

    assert response.status_code == exp_status_code


@pytest.mark.parametrize(
    "post_data",
    [
        [
            ("next_month", "next_month"),
            ("curr_year", f"{datetime.now().year}"),
            ("curr_month", f"{datetime.now().month}"),
        ],
        [
            ("next_month", "next_month"),
            ("curr_year", f"{datetime.now().year}"),
            ("curr_month", "12"),
        ],
        [
            ("prev_month", "prev_month"),
            ("curr_year", f"{datetime.now().year}"),
            ("curr_month", f"{datetime.now().month}"),
        ],
        [
            ("prev_month", "prev_month"),
            ("curr_year", f"{datetime.now().year}"),
            ("curr_month", "1"),
        ],
        [
            ("today", "today"),
        ],
    ],
)
def test_journal_nav(client: FlaskClient, post_data: list[tuple[str, str]]) -> None:
    response = client.post(
        "/overview/journal",
        data=MultiDict(post_data),
    )
    assert response.status_code == 200


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
    mock_enhancer = MagicMock

    def update_elevation(a: Any, track: GPXTrack, inplace: bool) -> None:
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


def test_view_bike_na(client: FlaskClient) -> None:
    response = client.get(f"/bike/{uuid.uuid4()}/")
    assert response.status_code == 302


def test_view_all_rides(app: Flask, client: FlaskClient) -> None:
    with app.app_context():
        ride_ids = [r.id for r in Ride.query.all()]

    for ride_id in ride_ids:
        response = client.get(f"/ride/{ride_id}/")
        assert response.status_code == 200


def test_view_all_bikes(app: Flask, client: FlaskClient) -> None:
    with app.app_context():
        bike_names = [b.name for b in Bike.query.all()]

    for name in bike_names:
        response = client.get(f"/bike/{name}/")
        assert response.status_code == 200


def test_view_all_segments(app: Flask, client: FlaskClient) -> None:
    with app.app_context():
        segment_ids = [s.id for s in DatabaseSegment.query.all()]

    for segment_id in segment_ids:
        response = client.get(f"segments/show/{segment_id}")
        assert response.status_code == 200
