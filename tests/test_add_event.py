from datetime import datetime
from typing import Any

import pytest
from flask import Flask
from flask.testing import FlaskClient
from werkzeug.datastructures import MultiDict

from cycle_analytics.database.model import DatabaseEvent, Ride
from cycle_analytics.database.model import db as orm_db
from cycle_analytics.database.retriever import get_unique_model_objects_in_db


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
        events_pre = get_unique_model_objects_in_db(DatabaseEvent)
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
        events_post = get_unique_model_objects_in_db(DatabaseEvent)
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
        events_pre = get_unique_model_objects_in_db(DatabaseEvent)
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
        events_post = get_unique_model_objects_in_db(DatabaseEvent)
        id_max_post = max([e.id for e in events_post])
        assert id_max_post > id_max_pre
        ride_post = orm_db.get_or_404(Ride, 4)
        assert len(ride_post.events) > len(ride_pre.events)
