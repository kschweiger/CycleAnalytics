from abc import ABC, abstractmethod
from copy import copy
from datetime import date
from enum import Enum
from typing import Dict

import numpy as np
import pandas as pd


class GoalType(str, Enum):
    COUNT = "count"
    TOTAL_DISTANCE = "total_distance"
    AVG_DISTANCE = "avg_distance"
    MAX_DISTANCE = "max_distance"

    @property
    def description(self) -> str:
        if self == GoalType.COUNT:
            return "Count rides"
        elif self == GoalType.TOTAL_DISTANCE:
            return "Total distance in time span"
        elif self == GoalType.AVG_DISTANCE:
            return "Average monthly distance"
        elif self == GoalType.MAX_DISTANCE:
            return "Maximum ride distance"
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
        elif self == GoalType.MAX_DISTANCE:
            return f"{threshold} km"
        else:
            raise NotImplementedError


class Goal(ABC):
    def __init__(self, **kwargs) -> None:
        self.name: str = kwargs["goal_name"]
        self.id: int = kwargs["id_goal"]
        self.description: None | str = kwargs["description"]
        self.type = GoalType(kwargs["type"])
        self.threshold: float = kwargs["threshold"]
        self.is_upper_bound: bool = kwargs["is_upper_bound"]
        self.year: int = kwargs["year"]
        self.month: None | int = None
        self.reached: bool = kwargs["has_been_reached"]
        self.constraints: None | Dict[str, list[str]] = kwargs["constraints"]
        self.active: bool = kwargs["active"]

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
        elif self.type == GoalType.MAX_DISTANCE:
            return data.distance.max()
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

    def evaluate(self, data: pd.DataFrame) -> tuple[bool, float, float]:
        """Evaluate the goal gainst the passed data. Returns boolen flag and
        a numerical progress. The numberical progress is a number between 0 and 1
        (%) if the goal threshold is an upper_bound and the difference to the threshold
        if the threshold is a lower bound.

        :param data: Data to be evaluated
        :return: Tuple containing boolean flag specifiying if the gial has been
                 reached and a float specifying the progress.
        """
        relevant_data = self._get_relevant_data(self._apply_constraints(data))
        if relevant_data.empty:
            return False, 0, 0 if self.is_upper_bound else np.nan

        curr_value = self._compute_value(relevant_data)

        if self.is_upper_bound:
            if curr_value == 0:
                progress = 0.0
            else:
                progress = curr_value / self.threshold
        else:
            progress = self.threshold - curr_value

        return self._check(curr_value), curr_value, progress

    @property
    @abstractmethod
    def goal_type_repr(self) -> str:
        ...

    def _apply_constraints(self, data: pd.DataFrame) -> pd.DataFrame:
        if self.constraints is None:
            return data

        mask = pd.Series(len(data) * [True])
        if "ride_type" in self.constraints.keys():
            mask = mask & data.ride_type.isin(self.constraints["ride_type"])

        if "bike" in self.constraints.keys():
            mask = mask & data.bike.isin(self.constraints["bike"])

        return data[mask]


class YearlyGoal(Goal):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

    def _get_relevant_data(self, data: pd.DataFrame) -> pd.DataFrame:
        year_begin = date(self.year, 1, 1)
        year_end = date(self.year, 12, 31)

        return data[(data.date >= year_begin) & (data.date <= year_end)]

    @property
    def goal_type_repr(self) -> str:
        return "YearlyGoal"


class MonthlyGoal(Goal):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.month: int = kwargs["month"]

        if self.month is None or self.month < 1 or self.month > 12:
            raise ValueError("Month has to be in [1,12]")

    def _get_relevant_data(self, data: pd.DataFrame) -> pd.DataFrame:
        month_start = date(self.year, self.month, 1)
        if self.month == 12:
            next_month_start = date(self.year + 1, 1, 1)
        else:
            next_month_start = date(self.year, self.month + 1, 1)

        return data[(data.date >= month_start) & (data.date < next_month_start)]

    @property
    def goal_type_repr(self) -> str:
        return "MonthlyGoal"


class LocationGoal(YearlyGoal):
    def __init__(self, **kwargs) -> None:
        # Location is defined in the constraints database field so wee
        # we need it to be present
        if kwargs["constraints"] is None:
            raise RuntimeError
        # Aklso the lcoation contraint has to be set
        if "location" not in kwargs["constraints"]:
            raise RuntimeError

        super().__init__(**kwargs)

    @property
    def goal_type_repr(self) -> str:
        return "LocationGoal"

    def evaluate(self, data: pd.DataFrame) -> tuple[bool, float, float]:
        relevant_data = self._get_relevant_data(self._apply_constraints(data))

        for track_row in relevant_data.to_dict("recordes"):
            # TODO: Check if the track contains the location
            ...


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