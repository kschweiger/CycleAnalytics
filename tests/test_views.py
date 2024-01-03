from datetime import datetime
from typing import Any

import pytest
from flask import Flask
from flask.testing import FlaskClient
from werkzeug.datastructures import MultiDict

from cycle_analytics.database.model import DatabaseEvent, Ride
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


@pytest.mark.parametrize(
    ("add_data", "check_data"),
    [
        (
            [("severity", "-1"), ("bike", "-1"), ("description", "")],
            {"id_severity": None, "id_bike": None, "description": None},
        ),
        (
            [("severity", "-1"), ("bike", "-1"), ("description", "Some text")],
            {"id_severity": None, "id_bike": None, "description": "Some text"},
        ),
        (
            [("severity", "1"), ("bike", "1"), ("description", "")],
            {"id_severity": 1, "id_bike": 1, "description": None},
        ),
        (
            [
                ("severity", "-1"),
                ("bike", "-1"),
                ("description", ""),
                ("latitude", "22.22"),
                ("longitude", "33.33"),
            ],
            {
                "id_severity": None,
                "id_bike": None,
                "description": None,
                "latitude": 22.22,
                "longitude": 33.33,
            },
        ),
    ],
)
def test_add_event(
    app: Flask,
    client: FlaskClient,
    add_data: list[tuple[str, str]],
    check_data: dict[str, Any],
) -> None:
    this_year = datetime.now().year
    this_month = datetime.now().month
    with app.app_context():
        events_pre = DatabaseEvent.query.all()
        id_max_pre = max([e.id for e in events_pre])

    post_data = MultiDict(
        [
            ("date", f"{this_year}-{this_month}-3"),
            ("event_type", "1"),
            ("short_description", "Some text"),
        ]
        + add_data
    )
    response = client.post("/add/event", data=post_data, follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        events_post = DatabaseEvent.query.all()
        id_max_post = max([e.id for e in events_post])
        assert id_max_post > id_max_pre
        new_event = events_post[-1]
        for key, value in check_data.items():
            assert getattr(new_event, key) == value


def test_add_event_from_ride(
    app: Flask,
    client: FlaskClient,
) -> None:
    this_year = datetime.now().year

    with app.app_context():
        events_pre = DatabaseEvent.query.all()
        id_max_pre = max([e.id for e in events_pre])
        ride_pre = orm_db.get_or_404(Ride, 4)
        ride_pre.events

    post_data = MultiDict(
        [
            ("event_type", "1"),
            ("short_description", "Some text"),
            ("severity", "-1"),
            ("bike", "-1"),
            ("description", ""),
        ]
    )

    response = client.post(
        f"/add/event?date={this_year}-08-01&id_ride=4",
        data=post_data,
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        events_post = DatabaseEvent.query.all()
        id_max_post = max([e.id for e in events_post])
        assert id_max_post > id_max_pre
        ride_post = orm_db.get_or_404(Ride, 4)
        assert len(ride_post.events) > len(ride_pre.events)
