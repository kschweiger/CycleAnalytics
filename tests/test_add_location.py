import pytest
from flask import Flask
from flask.testing import FlaskClient
from sqlalchemy import select
from werkzeug.datastructures import MultiDict

from cycle_analytics.database.model import DatabaseLocation
from cycle_analytics.database.model import db as orm_db


@pytest.mark.parametrize(
    ("post_data", "exp_attrs"),
    [
        (
            [
                ("name", "Added location 1"),
                ("latitude", "40"),
                ("longitude", "9.25"),
                ("description", ""),
            ],
            dict(
                name="Added location 1",
                latitude=40,
                longitude=9.25,
                description=None,
            ),
        ),
        (
            [
                ("name", "Added location 2"),
                ("latitude", "40.05"),
                ("longitude", "9"),
                ("description", "Some description"),
            ],
            dict(
                name="Added location 2",
                latitude=40.05,
                longitude=9,
                description="Some description",
            ),
        ),
    ],
)
def test_add_location(
    app: Flask, client: FlaskClient, post_data: list[tuple[str, str]], exp_attrs: dict
) -> None:
    with app.app_context():
        stmt = select(DatabaseLocation)
        locations_pre = orm_db.session.scalars(stmt).unique().all()
        max_id_pre = max([loc.id for loc in locations_pre])

    _post_data = MultiDict(post_data)

    response = client.post(
        "/add/location",
        data=_post_data,
        follow_redirects=True,
    )
    assert response.status_code == 200

    with app.app_context():
        stmt = select(DatabaseLocation)
        locations_pre = orm_db.session.scalars(stmt).unique().all()
        max_id_post = max([loc.id for loc in locations_pre])
        assert max_id_post > max_id_pre

        test_location = orm_db.get_or_404(DatabaseLocation, max_id_post)

        for key, value in exp_attrs.items():
            assert getattr(test_location, key) == value
