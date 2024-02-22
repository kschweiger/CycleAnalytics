from datetime import date
from typing import Type

import pandas as pd
import pytest

from cycle_analytics.model.goal import (
    AggregationType,
    ConciseGoal,
    Goal,
    GoalEvaluation,
    ManualGoal,
    RideGoal,
    TemporalType,
    agg_ride_goal,
    format_goals_concise,
)


@pytest.mark.parametrize(
    ("agg_type", "exp_value"),
    [
        (AggregationType.COUNT, 3),
        (AggregationType.TOTAL_DISTANCE, 41),
        (AggregationType.AVG_DISTANCE, 41 / 3),
        (AggregationType.MAX_DISTANCE, 17),
    ],
)
def test_agg_ride_goal(agg_type: AggregationType, exp_value: int | float) -> None:
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

    assert agg_ride_goal(data, agg_type) == exp_value


@pytest.mark.parametrize(
    ("agg_type", "threshold", "text"),
    [
        (AggregationType.COUNT, 5, "5 occurances"),
        (AggregationType.TOTAL_DISTANCE, 1000, "1000 m"),
        (AggregationType.TOTAL_DISTANCE, 10000, "10.0 km"),
        (AggregationType.MAX_DISTANCE, 5, "5 km"),
    ],
)
def test_agg_get_formatted_condition(
    agg_type: AggregationType, threshold: float, text: str
) -> None:
    assert agg_type.get_formatted_condition(threshold) == text


@pytest.mark.parametrize("goal_type", [RideGoal, ManualGoal])
@pytest.mark.parametrize(
    ("year", "month", "exp_temporal_type"), [(2022, None, TemporalType.YEARLY)]
)
def test_temporal_type(
    goal_type: Type[Goal], year: int, month: None | int, exp_temporal_type: TemporalType
) -> None:
    init_args = {
        "id": 1,
        "name": "SomeName",
        "agg_type": AggregationType.COUNT,
        "threshold": 10,
        "is_upper_bound": True,
        "description": "Description YearlyGoal",
        "reached": False,
        "constraints": None,
        "active": True,
        "value": None,
    }

    goal = goal_type(year=year, month=month, **init_args)

    assert goal.temporal_type == exp_temporal_type


@pytest.mark.parametrize(
    ("year", "month", "exp_eval", "temp_type"),
    [
        (2022, 1, GoalEvaluation(False, 3, 3 / 5), TemporalType.MONTHLY),
        (2022, 5, GoalEvaluation(False, 0, 0), TemporalType.MONTHLY),
        (2021, 12, GoalEvaluation(False, 1, 1 / 5), TemporalType.MONTHLY),
        (2022, None, GoalEvaluation(True, 6, 6 / 5), TemporalType.YEARLY),
    ],
)
def test_ride_goal(
    year: int, month: None | int, exp_eval: GoalEvaluation, temp_type: TemporalType
) -> None:
    init_args = {
        "id": 1,
        "name": "SomeName",
        "agg_type": AggregationType.COUNT,
        "threshold": 5,
        "is_upper_bound": True,
        "description": "Description YearlyGoal",
        "reached": False,
        "constraints": None,
        "active": True,
        "value": None,
    }

    data = pd.DataFrame(
        {
            "date": [
                date(2022, 1, 1),
                date(2022, 1, 2),
                date(2022, 1, 3),
                date(2022, 2, 3),
                date(2022, 2, 4),
                date(2022, 2, 6),
                date(2021, 12, 6),
            ],
            "distance": [11, 13, 17, 22, 10, 5, 1],
        }
    )

    goal = RideGoal(**init_args, year=year, month=month)

    assert goal.temporal_type == temp_type

    assert goal.evaluate(data) == exp_eval


@pytest.mark.parametrize(
    ("month", "temp_type"), [(None, TemporalType.YEARLY), (1, TemporalType.MONTHLY)]
)
@pytest.mark.parametrize(
    ("year", "value", "exp_eval"),
    [
        (2022, None, GoalEvaluation(False, 0, 0)),
        (2022, 2, GoalEvaluation(False, 2, 2 / 5)),
    ],
)
def test_manual_goal(
    year: int,
    month: None | int,
    value: None | float,
    exp_eval: GoalEvaluation,
    temp_type: TemporalType,
) -> None:
    init_args = {
        "id": 1,
        "name": "SomeName",
        "agg_type": AggregationType.COUNT,
        "threshold": 5,
        "is_upper_bound": True,
        "description": "Description YearlyGoal",
        "reached": False,
        "constraints": None,
        "active": True,
    }

    goal = ManualGoal(**init_args, year=year, month=month, value=value)

    assert goal.temporal_type == temp_type

    assert goal.evaluate() == exp_eval


@pytest.mark.parametrize(("goal_type", "value"), [(ManualGoal, 2), (RideGoal, None)])
@pytest.mark.parametrize("month", [None, 1])
@pytest.mark.parametrize("reached", [True, False])
def test_format_goals_concise(
    goal_type: Type[Goal], value: None | int, month: None | int, reached: bool
) -> None:
    init_args = {
        "year": 2024,
        "month": month,
        "id": 1,
        "name": "SomeName",
        "agg_type": AggregationType.COUNT,
        "threshold": 5,
        "is_upper_bound": True,
        "description": "Description",
        "reached": reached,
        "constraints": None,
        "active": True,
        "value": value,
    }

    goal = goal_type(**init_args)

    res = format_goals_concise([goal])[0]

    assert isinstance(res, ConciseGoal)

    assert res.name == init_args["name"]
    assert res.reached == reached


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
        "agg_type": AggregationType.COUNT,
        "threshold": 5,
        "is_upper_bound": True,
        "description": "Description YearlyGoal",
        "reached": False,
        "constraints": constraints,
        "active": True,
        "value": None,
    }
    goal = RideGoal(**kwargs)

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
