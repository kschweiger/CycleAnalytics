import uuid
from typing import Literal

import pytest
from flask import Flask, get_flashed_messages
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
def test_mod_manual_count_goal(
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


@pytest.mark.parametrize("month", [None, 1])
@pytest.mark.parametrize(
    ("initial_value", "mod_value", "exp_value"),
    [
        (None, "20", 20),
        (30, "60", 60),
        (10, "15.5", 15.5),
    ],
)
def test_mod_manual_decimal(
    app: Flask,
    client: FlaskClient,
    month: None | int,
    initial_value: None | float,
    mod_value: Literal["increase", "decrease"],
    exp_value: float,
) -> None:
    name = f"mod_decimal_{uuid.uuid4()}"
    with app.app_context():
        database_goal = DatabaseGoal(
            year=2020,
            month=month,
            name=name,
            goal_type="manual",
            aggregation_type="duration",
            threshold=60,
            is_upper_bound=True,
            value=initial_value,
        )
        orm_db.session.add(database_goal)
        orm_db.session.commit()
        goal_id = database_goal.id

    post_data = MultiDict(
        [("value_manua_goal_id", goal_id), ("change_value", mod_value)]
    )

    response = client.post(
        "goals/",
        data=post_data,
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        database_goal = orm_db.get_or_404(DatabaseGoal, goal_id)
        assert database_goal.value == exp_value


@pytest.mark.parametrize(
    ("value_manua_goal_id", "change_value", "aggregation_type", "exp_error"),
    [
        (
            987456321,
            "increase",
            "count",
            "An error corrured with change state if goal 987456321",
        ),
        (
            987456321,
            "decrease",
            "count",
            "An error corrured with change state if goal 987456321",
        ),
        (
            987456321,
            "10",
            "duration",
            "An error corrured with change state if goal 987456321",
        ),
        (None, "blub", "duration", "Passed value blub is not valid. Pass a number"),
    ],
)
def test_modify_manual_errors(
    app: Flask,
    client: FlaskClient,
    value_manua_goal_id: int | None,
    change_value: str,
    aggregation_type: str,
    exp_error: str,
) -> None:
    name = f"mod_errors_{uuid.uuid4()}"
    with app.app_context():
        database_goal = DatabaseGoal(
            year=2020,
            month=None,
            name=name,
            goal_type="manual",
            aggregation_type=aggregation_type,
            threshold=60,
            is_upper_bound=True,
            value=None,
        )
        orm_db.session.add(database_goal)
        orm_db.session.commit()
        goal_id = database_goal.id

    post_data = MultiDict(
        [
            (
                "value_manua_goal_id",
                goal_id if value_manua_goal_id is None else value_manua_goal_id,
            ),
            ("change_value", change_value),
        ]
    )
    with client:
        response = client.post(
            "goals/",
            data=post_data,
            follow_redirects=True,
        )
        assert response.status_code == 200
        messages = get_flashed_messages()
        assert len(messages) == 1
        assert messages[0] == exp_error
