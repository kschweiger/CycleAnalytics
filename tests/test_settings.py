import json
import re

import pytest
from flask import Flask
from flask.testing import FlaskClient
from geo_track_analyzer.model import ZoneInterval
from werkzeug.datastructures import MultiDict

from cycle_analytics.database.retriever import get_zones_for_metric
from cycle_analytics.settings import Action, _update_zones


@pytest.mark.parametrize(
    ("intervals_in", "intervals_out", "action"),
    [
        (
            [ZoneInterval(start=None, end=100), ZoneInterval(start=100, end=None)],
            [ZoneInterval(start=None, end=100), ZoneInterval(start=100, end=None)],
            None,
        ),
        (
            [ZoneInterval(start=None, end=100), ZoneInterval(start=100, end=None)],
            [
                ZoneInterval(start=None, end=100),
                ZoneInterval(start=100, end=101),
                ZoneInterval(start=101, end=None),
            ],
            Action.ADD,
        ),
        (
            [
                ZoneInterval(name="Z1", start=None, end=100),
                ZoneInterval(name="Z2", start=100, end=None),
            ],
            [
                ZoneInterval(name="Z1", start=None, end=100),
                ZoneInterval(name="Z2", start=100, end=101),
                ZoneInterval(name="Added Zone", start=101, end=None),
            ],
            Action.ADD,
        ),
        (
            [
                ZoneInterval(start=None, end=100),
                ZoneInterval(start=100, end=101),
                ZoneInterval(start=101, end=None),
            ],
            [
                ZoneInterval(start=None, end=100),
                ZoneInterval(start=100, end=None),
            ],
            Action.REMOVE,
        ),
    ],
)
def test_update_zones(
    intervals_in: list[ZoneInterval],
    intervals_out: list[ZoneInterval],
    action: None | Action,
) -> None:
    assert intervals_out == _update_zones(intervals_in, action)


@pytest.mark.parametrize(
    ("action", "exp_count"), [(None, 3), ("add", 4), ("remove", 2)]
)
def test_get_zone_form(client: FlaskClient, action: None | str, exp_count: int) -> None:
    intervals = [
        ZoneInterval(name="Zone 1", start=None, end=100, color=None),
        ZoneInterval(name="Zone 2", start=100, end=150, color=None),
        ZoneInterval(name="Zone 3", start=150, end=None, color=None),
    ]
    post_data = json.dumps(
        {"intervals": [json.dumps(i.model_dump()) for i in intervals]}
    )

    query_string = None if action is None else {"action": action}

    response = client.post(
        "/settings/get_zone_form/",
        query_string=query_string,
        data=post_data,
        follow_redirects=False,
        content_type="application/json",
    )
    assert response.status_code == 200
    pattern = r'<input class="form-control" type="text" id="name_'
    match = re.findall(pattern, response.get_json()["data"])
    assert match is not None
    assert len(match) == exp_count


def test_modify_zones_update(
    app: Flask,
    client: FlaskClient,
) -> None:
    with app.app_context():
        zones_pre = get_zones_for_metric("power")
    assert zones_pre is not None
    assert len(zones_pre.intervals) == 2

    post_data = MultiDict(
        [
            ("count_zones", "3"),
            ("name_1", "1"),
            ("end_1", "50"),
            ("color_1", "#ff0000"),
            ("name_2", "2"),
            ("start_2", "50"),
            ("end_2", "150"),
            ("color_2", "#00ff00"),
            ("name_3", "3"),
            ("start_3", "150"),
            ("color_3", "#0000ff"),
        ]
    )

    response = client.post("/settings/modify_zones/power", data=post_data)

    assert response.status_code == 200

    with app.app_context():
        zones_post = get_zones_for_metric("power")
    assert zones_post is not None
    assert len(zones_post.intervals) == 3
    assert [i.start for i in zones_post.intervals] == [None, 50, 150]
    assert [i.end for i in zones_post.intervals] == [50, 150, None]
    assert [i.name for i in zones_post.intervals] == ["1", "2", "3"]
    assert [i.color for i in zones_post.intervals] == ["#ff0000", "#00ff00", "#0000ff"]


def test_modify_zones_initial(
    app: Flask,
    client: FlaskClient,
) -> None:
    with app.app_context():
        zones_pre = get_zones_for_metric("cadence")
    assert zones_pre is None

    post_data = MultiDict(
        [
            ("count_zones", "3"),
            ("name_1", "1"),
            ("end_1", "50"),
            ("color_1", "#ff0000"),
            ("name_2", "2"),
            ("start_2", "50"),
            ("end_2", "150"),
            ("color_2", "#00ff00"),
            ("name_3", "3"),
            ("start_3", "150"),
            ("color_3", "#0000ff"),
        ]
    )

    response = client.post("/settings/modify_zones/cadence", data=post_data)

    assert response.status_code == 200

    with app.app_context():
        zones_post = get_zones_for_metric("cadence")
    assert zones_post is not None
    assert len(zones_post.intervals) == 3
