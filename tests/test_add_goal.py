import uuid
from datetime import datetime
from typing import Any

import pytest
from flask import Flask
from flask.testing import FlaskClient
from sqlalchemy import select
from werkzeug.datastructures import MultiDict

from cycle_analytics.database.model import DatabaseGoal
from cycle_analytics.database.model import db as orm_db
from cycle_analytics.model.goal import GoalType


@pytest.mark.parametrize(
    ("add_post_data", "check_data", "route", "filter_type"),
    [
        (
            [
                ("month", "-1"),
                ("aggregation_type", "count"),
                ("threshold", "10"),
                ("boundary", "1"),
            ],
            {
                "month": None,
                "aggregation_type": "count",
                "is_upper_bound": True,
                "threshold": 10.0,
                "constraints": None,
            },
            "/add/goal/ride",
            GoalType.RIDE,
        ),
        (
            [
                ("month", "-1"),
                ("aggregation_type", "count"),
                ("threshold", "10"),
                ("boundary", "0"),
            ],
            {
                "month": None,
                "aggregation_type": "count",
                "is_upper_bound": False,
                "threshold": 10.0,
                "constraints": None,
            },
            "/add/goal/ride",
            GoalType.RIDE,
        ),
        (
            [
                ("month", "0"),
                ("aggregation_type", "count"),
                ("threshold", "10"),
                ("boundary", "1"),
            ],
            {
                "month": 0,
                "aggregation_type": "count",
                "is_upper_bound": True,
                "threshold": 10.0,
                "constraints": None,
            },
            "/add/goal/ride",
            GoalType.RIDE,
        ),
        (
            [
                ("month", "12"),
                ("aggregation_type", "count"),
                ("threshold", "10"),
                ("boundary", "1"),
            ],
            {
                "month": 12,
                "aggregation_type": "count",
                "is_upper_bound": True,
                "threshold": 10.0,
                "constraints": None,
            },
            "/add/goal/ride",
            GoalType.RIDE,
        ),
        (
            [
                ("month", "12"),
                ("aggregation_type", "count"),
                ("threshold", "10"),
                ("boundary", "1"),
                ("bike", "Bike 1"),
                ("bike", "Bike 2"),
            ],
            {
                "constraints": {"bike": ["Bike 1", "Bike 2"]},
            },
            "/add/goal/ride",
            GoalType.RIDE,
        ),
        (
            [
                ("month", "12"),
                ("aggregation_type", "count"),
                ("threshold", "10"),
                ("boundary", "1"),
                ("ride_types", "MTB"),
                ("ride_types", "Road"),
            ],
            {
                "constraints": {"ride_type": ["MTB", "Road"]},
            },
            "/add/goal/ride",
            GoalType.RIDE,
        ),
        (
            [
                ("month", "12"),
                ("aggregation_type", "count"),
                ("threshold", "10"),
                ("boundary", "1"),
                ("bike", "Bike 1"),
                ("bike", "Bike 2"),
                ("ride_types", "MTB"),
                ("ride_types", "Road"),
            ],
            {
                "constraints": {
                    "bike": ["Bike 1", "Bike 2"],
                    "ride_type": ["MTB", "Road"],
                },
            },
            "/add/goal/ride",
            GoalType.RIDE,
        ),
        # ~~~~~~~~~~~~~~ MANUAL GOALS ~~~~~~~~~~~~~~~~~~~
        (
            [
                ("month", "0"),
                ("aggregation_type", "count"),
                ("threshold", "10"),
                ("boundary", "1"),
            ],
            {
                "month": 0,
                "aggregation_type": "count",
                "is_upper_bound": True,
                "threshold": 10.0,
                "constraints": None,
            },
            "/add/goal/manual",
            GoalType.MANUAL,
        ),
        (
            [
                ("month", "12"),
                ("aggregation_type", "count"),
                ("threshold", "10"),
                ("boundary", "1"),
            ],
            {
                "month": 12,
                "aggregation_type": "count",
                "is_upper_bound": True,
                "threshold": 10.0,
                "constraints": None,
            },
            "/add/goal/manual",
            GoalType.MANUAL,
        ),
    ],
)
def test_add_goal(
    app: Flask,
    client: FlaskClient,
    add_post_data: list[tuple[str, str]],
    check_data: dict[str, Any],
    route: str,
    filter_type: GoalType,
) -> None:
    last_year = datetime.now().year - 1

    with app.app_context():
        stmt = select(DatabaseGoal).filter(
            (DatabaseGoal.year == last_year) & (DatabaseGoal.goal_type == filter_type)
        )
        goals_pre = orm_db.session.scalars(stmt).unique().all()
        if goals_pre:
            max_id_pre = max([g.id for g in goals_pre])
        else:
            max_id_pre = -1

    name = str(uuid.uuid4())
    post_data = MultiDict([("name", name), ("year", str(last_year))] + add_post_data)

    response = client.post(
        route,
        data=post_data,
        follow_redirects=True,
    )
    assert response.status_code == 200

    with app.app_context():
        stmt = select(DatabaseGoal).filter(
            (DatabaseGoal.year == last_year) & (DatabaseGoal.goal_type == filter_type)
        )
        goals = orm_db.session.scalars(stmt).unique().all()
        max_id_post = max([g.id for g in goals])
        assert max_id_post > max_id_pre

        test_goal = orm_db.get_or_404(DatabaseGoal, max_id_post)

        assert test_goal.name == name
        assert test_goal.year == last_year
        for key, value in check_data.items():
            assert getattr(test_goal, key) == value
