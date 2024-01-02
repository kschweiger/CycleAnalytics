import pytest
from flask.testing import FlaskClient


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
        ("/goals/", 200),
        ("/events/", 200),
        ("/segments/", 200),
        ("/add/ride", 200),
        ("/add/event", 200),
        ("/add/goal", 200),
        ("/ride/1/", 200),
    ],
)
def test_views(client: FlaskClient, route: str, exp_status_code: int) -> None:
    response = client.get(route)

    assert response.status_code == exp_status_code
