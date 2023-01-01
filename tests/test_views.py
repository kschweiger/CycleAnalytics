import pytest


@pytest.mark.parametrize(
    "route", ["/", "/overview/", "/ride/1/", "/add/ride", "/settings/"]
)
def test_views(client, route):
    response = client.get(route)

    assert response.status_code == 200
