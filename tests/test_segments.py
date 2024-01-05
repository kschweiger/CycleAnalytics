import json
import uuid

import pytest
from flask.testing import FlaskClient
from werkzeug.datastructures import MultiDict

from cycle_analytics.segments import merge_route_segments


@pytest.mark.parametrize(
    "waypoints",
    [
        [[47.9684, 7.843532], [47.968891, 7.840834]],
        [[47.9684, 7.843532], [47.968891, 7.840834], [47.968132, 7.840869]],
    ],
)
def test_calc_route(client: FlaskClient, waypoints: list[list[float]]) -> None:
    response = client.post(
        "segments/calc-route",
        headers={"Content-Type": "application/json"},
        data=json.dumps({"waypoints": waypoints}),
    )
    assert response.status_code == 200
    assert response.json is not None
    assert "route" in response.json.keys()
    assert isinstance(response.json["route"], list)


@pytest.mark.parametrize(
    ("segments", "ret_value"),
    [
        (
            [[(1, 1), (1, 2), (1, 3)], [(1, 3), (1, 2), (2, 2), (3, 3)]],
            [(1, 1), (1, 2), (2, 2), (3, 3)],
        )
    ],
)
def test_merge_route_segments(
    segments: list[list[tuple[float, float]]], ret_value: list[tuple[float, float]]
) -> None:
    assert merge_route_segments(segments) == ret_value


@pytest.mark.parametrize(
    "add_post_data",
    [
        [
            ("segment_latitudes", "47.99342675970,47.994322305132,47.99480783564"),
        ],
        [
            ("segment_elevations", "100,105,110"),
            ("segment_latitudes", "47.99442675970,47.995322305132,47.99580783564"),
        ],
    ],
)
def test_add_segment(
    client: FlaskClient,
    add_post_data: list[tuple[str, str]],
) -> None:
    name = f"Segment {uuid.uuid4()}"

    post_data = MultiDict(
        [
            ("segment_longitudes", "7.8488553829272,7.849434907712,7.849898971781"),
            ("segment_name", name),
            ("segment_type", "1"),
            ("segment_difficulty", "1"),
        ]
        + add_post_data
    )
    response = client.post("/segments/add", data=post_data)

    assert response.status_code == 302
