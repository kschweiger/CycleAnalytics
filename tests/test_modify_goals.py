import uuid
from typing import Literal

import pytest
from flask import Flask
from flask.testing import FlaskClient
from werkzeug.datastructures import MultiDict

from cycle_analytics.database.model import DatabaseGoal
from cycle_analytics.database.model import db as orm_db


@pytest.mark.parametrize("month", [None, 1])
@pytest.mark.parametrize(
    ("value", "action", "exp_value"),
    [
        (None, "increase", 1),
        (0, "increase", 1),
        (1, "increase", 2),
        (1, "decrease", 0),
        (4, "decrease", 3),
    ],
)
def test_mad_manual_count_goal(
    app: Flask,
    client: FlaskClient,
    month: None | int,
    value: None | float,
    action: Literal["increase", "decrease"],
    exp_value: float,
) -> None:
    name = str(uuid.uuid4())
    with app.app_context():
        database_goal = DatabaseGoal(
            year=2021,
            month=month,
            name=name,
            goal_type="manual",
            aggregation_type="count",
            threshold=500,
            is_upper_bound=True,
            value=value,
        )
        orm_db.session.add(database_goal)
        orm_db.session.commit()
        goal_id = database_goal.id
    post_data = MultiDict([("value_manua_goal_id", goal_id), ("change_value", action)])

    response = client.post(
        "goals/",
        data=post_data,
        follow_redirects=True,
    )
    assert response.status_code == 200

    with app.app_context():
        database_goal = orm_db.get_or_404(DatabaseGoal, goal_id)
        assert database_goal.value == exp_value
