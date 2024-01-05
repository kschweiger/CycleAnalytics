from datetime import datetime
from io import BytesIO
from unittest.mock import MagicMock

from flask import Flask
from flask.testing import FlaskClient
from gpxpy.gpx import GPXTrack
from pytest_mock import MockerFixture
from track_analyzer import ByteTrack, PyTrack
from werkzeug.datastructures import MultiDict

from cycle_analytics import adders
from cycle_analytics.database.model import Ride
from cycle_analytics.database.model import db as orm_db
from cycle_analytics.utils import track as track_utils


def test_add_ride_no_track(app: Flask, client: FlaskClient) -> None:
    this_year = datetime.now().year
    this_month = datetime.now().month
    with app.app_context():
        rides_pre = Ride.query.all()
        id_max_pre = max([r.id for r in rides_pre])
    post_data = MultiDict(
        [
            ("date", f"{this_year}-{this_month}-3"),
            ("start_time", "13:22:02"),
            ("total_time", "01:02:33"),
            ("distance", "8.234"),
            ("bike", "1"),
            ("ride_type", "1"),
        ]
    )
    response = client.post("/add/ride", data=post_data, follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        rides_post = Ride.query.all()
        id_max_post = max([r.id for r in rides_post])
        assert id_max_post > id_max_pre


# TODO: Add parametrization is_enhanced once added
def test_add_ride_with_track(
    mocker: MockerFixture, app: Flask, client: FlaskClient
) -> None:
    spy_get_track = mocker.spy(adders, "get_track_from_form")
    spy_init_db_track = mocker.spy(adders, "init_db_track_and_enhance")

    spy_get_enhancer = mocker.spy(track_utils, "get_enhancer")
    mocker.patch("cycle_analytics.utils.track.get_enhanced_db_track", return_value=None)

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
    post_data = MultiDict(
        [
            ("date", f"{this_year}-{this_month}-3"),
            ("start_time", "13:22:02"),
            ("total_time", "01:02:33"),
            ("distance", "8.234"),
            ("bike", "1"),
            ("ride_type", "1"),
            ("track", (BytesIO(track.get_xml().encode()), "track.gpx")),
        ]
    )

    response = client.post(
        "/add/ride",
        data=post_data,
        follow_redirects=True,
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    assert spy_get_track.call_count == 1
    assert spy_init_db_track.call_count == 1
    assert spy_get_enhancer.call_count == 0

    with app.app_context():
        rides_post = Ride.query.all()
        id_max_post = max([r.id for r in rides_post])
        ride = orm_db.get_or_404(Ride, id_max_post)
        assert len(ride.tracks) == 1


def test_add_ride_with_track_and_enhancer(
    mocker: MockerFixture, app: Flask, client: FlaskClient
) -> None:
    spy_get_track = mocker.spy(adders, "get_track_from_form")
    spy_init_db_track = mocker.spy(adders, "init_db_track_and_enhance")

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
    post_data = MultiDict(
        [
            ("date", f"{this_year}-{this_month}-3"),
            ("start_time", "13:22:02"),
            ("total_time", "01:02:33"),
            ("distance", "8.234"),
            ("bike", "1"),
            ("ride_type", "1"),
            ("track", (BytesIO(track.get_xml().encode()), "track.gpx")),
        ]
    )

    response = client.post(
        "/add/ride",
        data=post_data,
        follow_redirects=True,
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    assert spy_get_track.call_count == 1
    assert spy_init_db_track.call_count == 1

    with app.app_context():
        rides_post = Ride.query.all()
        id_max_post = max([r.id for r in rides_post])
        ride = orm_db.get_or_404(Ride, id_max_post)
        assert len(ride.tracks) == 2
        assert not ride.tracks[0].is_enhanced
        assert ride.tracks[1].is_enhanced
        enhanced_track = ByteTrack(ride.tracks[1].content)
        assert track.track.segments[0].points != enhanced_track.track.segments[0].points
