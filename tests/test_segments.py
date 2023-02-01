import json

import pytest

from cycle_analytics.segments import merge_route_segments


@pytest.mark.parametrize(
    "waypoints",
    [
        [[47.9684, 7.843532], [47.968891, 7.840834]],
        [[47.9684, 7.843532], [47.968891, 7.840834], [47.968132, 7.840869]],
    ],
)
def test_calc_route(client, waypoints):

    response = client.post(
        "segments/calc-route",
        headers={"Content-Type": "application/json"},
        data=json.dumps({"waypoints": waypoints}),
    )
    assert response.status_code == 200
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
def test_merge_route_segments(segments, ret_value):
    assert merge_route_segments(segments) == ret_value
