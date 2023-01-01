from abc import ABC, abstractmethod
from copy import copy
from datetime import date
from enum import Enum
from typing import Optional

import pandas as pd
from flask import Blueprint, render_template

from cycle_analytics.db import get_db


class GoalType(str, Enum):
    COUNT = "count"
    TOTAL_DISTANCE = "total_distance"
    AVG_DISTANCE = "avg_distance"

    @property
    def description(self) -> str:
        if self == GoalType.COUNT:
            return "Count rides"
        elif self == GoalType.TOTAL_DISTANCE:
            return "Total distance in time span"
        elif self == GoalType.AVG_DISTANCE:
            return "Average monthly distance"
        else:
            raise NotImplementedError

    def get_formatted_condition(self, threshold: float) -> str:
        if self == GoalType.COUNT:
            return f"{threshold} rides"
        elif self in [GoalType.TOTAL_DISTANCE, GoalType.AVG_DISTANCE]:
            if threshold >= 5000:
                return f"{threshold/1000} km"
            else:
                return f"{threshold} m"
        else:
            raise NotImplementedError


class Goal(ABC):
    def __init__(self, **kwargs):
        self.name: str = kwargs["goal_name"]
        self.id: int = kwargs["id_goal"]
        self.description: str = kwargs["description"]
        self.type = GoalType(kwargs["type"])
        self.threshold: float = kwargs["threshold"]
        self.is_upper_bound: bool = kwargs["is_upper_bound"]
        self.year: int = kwargs["year"]
        self.month: Optional[int] = None
        self.reached: bool = kwargs["has_been_reached"]

    def _check(self, value: int | float) -> bool:
        if self.is_upper_bound:
            return value >= self.threshold
        else:
            return value <= self.threshold

    @abstractmethod
    def _get_relevant_data(self, data: pd.DataFrame) -> pd.DataFrame:
        ...

    def _compute_value(self, data: pd.DataFrame) -> int | float:
        if self.type == GoalType.COUNT:
            return len(data)
        elif self.type == GoalType.TOTAL_DISTANCE:
            return data.distance.sum()
        elif self.type == GoalType.AVG_DISTANCE:
            return data.distance.mean()
        else:
            raise NotImplementedError("Type %s not yet implemented" % self.type)

    def has_been_reached(self, data: pd.DataFrame) -> bool:
        """
        Checks the passed data against the gaol settings

        :param data: Dataframe with columns *date*, *distance*
        :return: Boolean value specifiying if the gaol has been reached
        """
        relevant_data = self._get_relevant_data(data)
        if relevant_data.empty:
            return False

        return self._check(self._compute_value(relevant_data))

    @property
    @abstractmethod
    def goal_type_repr(self) -> str:
        ...


class YearlyGoal(Goal):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _get_relevant_data(self, data: pd.DataFrame) -> pd.DataFrame:
        year_begin = date(self.year, 1, 1)
        year_end = date(self.year, 12, 31)

        return data[(data.date >= year_begin) & (data.date <= year_end)]

    @property
    def goal_type_repr(self) -> str:
        return "YearlyGoal"


class MonthlyGoal(Goal):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.month: int = kwargs["month"]

        if self.month is None or self.month < 1 or self.month > 12:
            raise ValueError("Month has to be in [1,12]")

    def _get_relevant_data(self, data: pd.DataFrame) -> pd.DataFrame:
        month_start = date(self.year, self.month, 1)
        next_month_start = date(self.year, self.month + 1, 1)

        return data[(data.date >= month_start) & (data.date < next_month_start)]

    @property
    def goal_type_repr(self) -> str:
        return "MonthlyGoal"


def initialize_goals(
    columns: list[str], rows: list[list[None | str | float | int | bool]]
) -> list[Goal]:
    goals: list[Goal] = []

    for row in rows:
        data_dict = {col: val for col, val in zip(columns, row)}
        month = data_dict["month"]
        if month is None:
            goals.append(YearlyGoal(**data_dict))
        elif isinstance(month, int):
            if month == 0:
                for i in range(1, 13):
                    this_data_dict = copy(data_dict)
                    this_data_dict["month"] = i
                    goals.append(MonthlyGoal(**this_data_dict))
            elif 0 < month <= 12:
                goals.append(MonthlyGoal(**data_dict))
            else:
                raise ValueError("Value %s for month is invalid" % data_dict["month"])
        else:
            # Keep mypy happy
            raise RuntimeError

    return goals


def format_goals_concise(goals: list[Goal]) -> list[tuple[str, str, str, int]]:
    formatted_goals = []
    for goal in goals:
        formatted_goals.append(
            (
                goal.name,
                goal.goal_type_repr,
                goal.type.get_formatted_condition(goal.threshold),
                int(goal.reached),
            )
        )

    return formatted_goals


bp = Blueprint("goals", __name__, url_prefix="/goals")


@bp.route("/", methods=("GET", "POST"))
def overview():
    from cycle_analytics.queries import load_goals

    db = get_db()
    goals = load_goals(2022)

    return render_template("goals.html", active_page="goals")
