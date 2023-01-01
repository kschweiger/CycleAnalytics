from datetime import date

import pandas as pd
import pytest

from cycle_analytics.goals import MonthlyGoal, YearlyGoal, initialize_goals


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
        ],
    ]

    test_goals = initialize_goals(columns, test_data)

    assert len(test_goals) == 14


@pytest.mark.parametrize(
    ("goal_type", "exp_value"),
    [("count", 3), ("total_distance", 41), ("avg_distance", 41 / 3)],
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
    }
    goal = MonthlyGoal(**kwargs)
    data = pd.DataFrame(
        {
            "date": [
                date(2021, 1, 1),
                date(2021, 1, 2),
                date(2021, 1, 3),
                date(2021, 1, 4),
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
