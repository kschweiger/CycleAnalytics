from datetime import date

import pandas as pd
import pytest

from cycle_analytics.model.goal import MonthlyGoal, YearlyGoal, initialize_goals


def test_initialize_goals():
    columns = [
        "id_goal",
        "year",
        "month",
        "goal_name",
        "type",
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
def test_goal_compute_value(goal_type, exp_value):
    kwargs = {
        "id_goal": 1,
        "year": 2022,
        "month": None,
        "goal_name": "YearlyGoal",
        "type": goal_type,
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
def test_yearly_goal(is_upper_bound, threshold, exp_result):
    kwargs = {
        "id_goal": 1,
        "year": 2022,
        "month": None,
        "goal_name": "YearlyGoal",
        "type": "count",
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


def test_monthly_goal():
    kwargs = {
        "id_goal": 1,
        "year": 2022,
        "month": 2,
        "goal_name": "YearlyGoal",
        "type": "count",
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
def test_evaluate(goal_type, theshold, upper_bound, exp_check, exp_value, exp_progress):
    kwargs = {
        "id_goal": 1,
        "year": 2022,
        "month": None,
        "goal_name": "YearlyGoal",
        "type": goal_type,
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
def test_constraints(constraints, exp_len):
    kwargs = {
        "id_goal": 1,
        "year": 2022,
        "month": None,
        "goal_name": "YearlyGoal",
        "type": "count",
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
