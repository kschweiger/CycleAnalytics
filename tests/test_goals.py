from datetime import date

import pandas as pd
import pytest
from flask import Flask
from flask.testing import FlaskClient

from cycle_analytics.database.model import DatabaseGoal
from cycle_analytics.database.model import db as orm_db
from cycle_analytics.model.goal import MonthlyGoal, YearlyGoal, initialize_goals


def test_initialize_goals() -> None:
    columns = [
        "id",
        "year",
        "month",
        "name",
        "goal_type",
        "threshold",
        "is_upper_bound",
        "description",
        "has_been_reached",
        "constraints",
        "active",
    ]

    test_data = [
        [
            1,
            2022,
            None,
            "YearlyGoal",
            "count",
            5,
            True,
            "Description YearlyGoal",
            False,
            None,
            True,
        ],
        [
            1,
            2022,
            0,
            "MonthlyGoal_all",
            "total_distance",
            100,
            True,
            "Description MonthlyGoal_all",
            False,
            None,
            True,
        ],
        [
            1,
            2022,
            1,
            "MonthlyGoal_jan",
            "avg_distance",
            20,
            True,
            "Description MonthlyGoal_jan",
            False,
            None,
            True,
        ],
    ]

    test_goals = initialize_goals(columns, test_data)

    assert len(test_goals) == 14


@pytest.mark.parametrize(
    ("goal_type", "exp_value"),
    [
        ("count", 3),
        ("total_distance", 41),
        ("avg_distance", 41 / 3),
        ("max_distance", 17),
    ],
)
def test_goal_compute_value(goal_type: str, exp_value: int | float) -> None:
    kwargs = {
        "id": 1,
        "year": 2022,
        "month": None,
        "name": "YearlyGoal",
        "goal_type": goal_type,
        "threshold": 10,
        "is_upper_bound": True,
        "description": "Description YearlyGoal",
        "has_been_reached": False,
        "constraints": None,
        "active": True,
    }

    goal = YearlyGoal(**kwargs)

    data = pd.DataFrame(
        {
            "date": [
                date(2022, 1, 1),
                date(2022, 1, 2),
                date(2022, 1, 3),
            ],
            "distance": [11, 13, 17],
        }
    )

    assert goal._compute_value(data) == exp_value


@pytest.mark.parametrize(
    ("is_upper_bound", "threshold", "exp_result"),
    [(True, 2, True), (True, 4, False), (False, 4, True)],
)
def test_yearly_goal(is_upper_bound: bool, threshold: float, exp_result: bool) -> None:
    kwargs = {
        "id": 1,
        "year": 2022,
        "month": None,
        "name": "YearlyGoal",
        "goal_type": "count",
        "threshold": threshold,
        "is_upper_bound": is_upper_bound,
        "description": "Description YearlyGoal",
        "has_been_reached": False,
        "constraints": None,
        "active": True,
    }
    goal = YearlyGoal(**kwargs)
    data = pd.DataFrame(
        {
            "date": [
                date(2021, 1, 1),
                date(2022, 1, 1),
                date(2022, 2, 2),
                date(2022, 3, 3),
            ],
            "distance": [7, 11, 13, 17],
        }
    )

    assert goal.has_been_reached(data) == exp_result


def test_monthly_goal() -> None:
    kwargs = {
        "id": 1,
        "year": 2022,
        "month": 2,
        "name": "YearlyGoal",
        "goal_type": "count",
        "threshold": 3,
        "is_upper_bound": True,
        "description": "Description YearlyGoal",
        "has_been_reached": False,
        "constraints": None,
        "active": True,
    }
    goal = MonthlyGoal(**kwargs)
    data = pd.DataFrame(
        {
            "date": [
                date(2022, 1, 1),
                date(2022, 1, 2),
                date(2022, 1, 3),
                date(2022, 1, 4),
                date(2022, 2, 1),
                date(2022, 2, 2),
                date(2022, 3, 2),
                date(2022, 3, 3),
                date(2022, 3, 5),
                date(2022, 3, 6),
            ],
            "distance": [7, 11, 13, 17, 19, 23, 29, 31, 37, 41],
        }
    )

    assert not goal.has_been_reached(data)


@pytest.mark.parametrize(
    ("goal_type", "theshold", "upper_bound", "exp_check", "exp_value", "exp_progress"),
    [
        ("count", 3, True, True, 5, 5 / 3),
        ("count", 6, True, False, 5, 5 / 6),
        ("count", 3, False, False, 5, -2),
        ("count", 7, False, True, 5, 2),
        ("total_distance", 100, True, False, 67, 0.67),
        ("total_distance", 50, True, True, 67, 67 / 50),
        ("avg_distance", 15, True, False, (67 / 5), (67 / 5) / 15),
        ("avg_distance", 10, True, True, (67 / 5), (67 / 5) / 10),
    ],
)
def test_evaluate(
    goal_type: str,
    theshold: float,
    upper_bound: bool,
    exp_check: bool,
    exp_value: float,
    exp_progress: float,
) -> None:
    kwargs = {
        "id": 1,
        "year": 2022,
        "month": None,
        "name": "YearlyGoal",
        "goal_type": goal_type,
        "threshold": theshold,
        "is_upper_bound": upper_bound,
        "description": "Description YearlyGoal",
        "has_been_reached": False,
        "constraints": None,
        "active": True,
    }
    goal = YearlyGoal(**kwargs)
    data = pd.DataFrame(
        {
            "date": [
                date(2022, 1, 1),
                date(2022, 1, 2),
                date(2022, 1, 3),
                date(2022, 1, 4),
                date(2022, 2, 1),
            ],
            "distance": [7, 11, 13, 17, 19],
        }
    )

    check, current_value, progress = goal.evaluate(data)

    assert check == exp_check
    assert current_value == exp_value
    assert progress == exp_progress


@pytest.mark.parametrize(
    ("constraints", "exp_len"),
    [
        (None, 5),
        ({"ride_type": ["MTB"]}, 3),
        ({"bike": ["Bike1"]}, 1),
        ({"bike": ["Bike1", "Bike3"]}, 3),
        ({"bike": ["Bike2"], "ride_type": ["MTB"]}, 1),
    ],
)
def test_constraints(constraints: dict[str, list[str]], exp_len: int) -> None:
    kwargs = {
        "id": 1,
        "year": 2022,
        "month": None,
        "name": "YearlyGoal",
        "goal_type": "count",
        "threshold": 5,
        "is_upper_bound": True,
        "description": "Description YearlyGoal",
        "has_been_reached": False,
        "constraints": constraints,
        "active": True,
    }
    goal = YearlyGoal(**kwargs)

    data = pd.DataFrame(
        {
            "date": [
                date(2022, 1, 1),
                date(2022, 1, 2),
                date(2022, 1, 3),
                date(2022, 1, 4),
                date(2022, 2, 1),
            ],
            "distance": [7, 11, 13, 17, 19],
            "ride_type": ["MTB", "MTB", "MTB", "Road", "Road"],
            "bike": ["Bike1", "Bike2", "Bike4", "Bike3", "Bike3"],
        }
    )

    assert len(goal._apply_constraints(data)) == exp_len


def test_goal_change_state(app: Flask, client: FlaskClient) -> None:
    with app.app_context():
        test_goal = orm_db.get_or_404(DatabaseGoal, 1)
        assert test_goal.active

    response = client.post(
        "/goals/", data=dict(change_state_value="Deactivate", change_state_goal_id=1)
    )

    assert response.status_code == 200

    with app.app_context():
        test_goal = orm_db.get_or_404(DatabaseGoal, 1)
        assert not test_goal.active
        test_goal.active = True
        orm_db.session.commit()
