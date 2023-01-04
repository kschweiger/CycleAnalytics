import pytest


@pytest.mark.parametrize(
    "route",
    [
        "/",
        "/overview/",
        "/ride/1/",
        "/add/ride",
        "/add/event",
        "/add/goal",
        "/settings/",
    ],
)
def test_views(client, route):
    response = client.get(route)

    assert response.status_code == 200
