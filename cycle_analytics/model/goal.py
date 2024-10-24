from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import final

import numpy as np
import pandas as pd

from ..model.exceptions import GoalSetupError
from ..utils.base import format_float, format_seconds


@dataclass
class GoalEvaluation:
    reached: bool
    current: float
    progress: float


@dataclass
class ConciseGoal:
    name: str
    goal_type_repr: str
    condition: str
    reached: int


class TemporalType(str, Enum):
    YEARLY = "Yearly"
    MONTHLY = "Monthly"


class GoalType(str, Enum):
    MANUAL = "manual"
    RIDE = "ride"
    LOCATION = "location"


class AggregationType(str, Enum):
    COUNT = "count"
    TOTAL_DISTANCE = "total_distance"
    AVG_DISTANCE = "avg_distance"
    MAX_DISTANCE = "max_distance"
    DURATION = "duration"

    @property
    def description(self) -> str:
        if self == AggregationType.COUNT:
            return "Count occurances"
        elif self == AggregationType.TOTAL_DISTANCE:
            return "Total distance in time span"
        elif self == AggregationType.AVG_DISTANCE:
            return "Average monthly distance"
        elif self == AggregationType.MAX_DISTANCE:
            return "Maximum ride distance"
        elif self == AggregationType.DURATION:
            return "Duration"
        else:
            raise NotImplementedError

    def get_formatted_condition(
        self, threshold: float, goal_type: None | GoalType = None
    ) -> str:
        if self == AggregationType.COUNT:
            if goal_type == GoalType.RIDE:
                return f"{format_float(threshold)} rides"
            return f"{format_float(threshold)} occurances"
        elif self in [
            AggregationType.MAX_DISTANCE,
            AggregationType.TOTAL_DISTANCE,
            AggregationType.AVG_DISTANCE,
        ]:
            return f"{format_float(threshold)} km"
        elif self == AggregationType.DURATION:
            if threshold > 60 * 60:
                return format_seconds(int(threshold), to="hours", format="truncated")
            elif threshold > 120:
                return format_seconds(int(threshold), to="minutes", format="truncated")
            else:
                return format_seconds(int(threshold), to="seconds", format="truncated")
        else:
            raise NotImplementedError


def agg_ride_goal(data: pd.DataFrame, agg: AggregationType) -> float:
    if agg == AggregationType.COUNT:
        return len(data)
    elif agg == AggregationType.TOTAL_DISTANCE:
        return data.distance.sum()
    elif agg == AggregationType.AVG_DISTANCE:
        return data.distance.mean()
    elif agg == AggregationType.MAX_DISTANCE:
        return data.distance.max()
    elif agg == AggregationType.DURATION:
        relevant_data = data[["ride_time", "total_time"]].min(axis=1).dropna()
        if relevant_data.empty:
            return 0
        return relevant_data.max()
    else:
        raise NotImplementedError("Type %s not yet implemented" % agg)


def agg_manual_goal(value: float, agg: AggregationType) -> float:
    if agg in [AggregationType.COUNT, AggregationType.DURATION]:
        return value
    else:
        raise NotImplementedError("Type %s not yet implemented" % agg)


def agg_location_goal(data: pd.DataFrame, agg: AggregationType) -> float:
    if agg in [AggregationType.COUNT]:
        return len(data)
    else:
        raise NotImplementedError("Type %s not yet implemented" % agg)


def is_acceptable_aggregation(goal_type: GoalType, agg: AggregationType) -> bool:
    if goal_type == GoalType.MANUAL:
        return agg in [AggregationType.COUNT, AggregationType.DURATION]
    elif goal_type == GoalType.RIDE:
        return agg in [
            AggregationType.COUNT,
            AggregationType.TOTAL_DISTANCE,
            AggregationType.AVG_DISTANCE,
            AggregationType.MAX_DISTANCE,
            AggregationType.DURATION,
        ]
    elif goal_type == GoalType.LOCATION:
        return agg in [AggregationType.COUNT]
    else:
        raise NotImplementedError


class Goal(ABC):
    def __init__(
        self,
        name: str,
        id: int,
        description: str | None,
        aggregation_type: AggregationType,
        threshold: float,
        is_upper_bound: bool,
        year: int,
        month: None | int,
        reached: bool,
        constraints: None | dict[str, list[str] | float | int],
        active: bool,
        value: None | float,
    ) -> None:
        self.name = name
        self.id = id
        self.description = description
        self.aggregation_type = aggregation_type
        self.threshold = threshold
        self.is_upper_bound = is_upper_bound
        self.reached = reached
        self.constraints = constraints
        self.active = active
        self.value = value

        self.year = year
        self.month = month

        if self.month is not None:
            if self.month < 1 or self.month > 12:
                raise ValueError("Month has to be in [1,12]")

    @property
    def temporal_type(self) -> TemporalType:
        if self.month is not None:
            return TemporalType.MONTHLY
        else:
            return TemporalType.YEARLY

    def _check(self, value: int | float) -> bool:
        if self.is_upper_bound:
            return value >= self.threshold
        else:
            return value <= self.threshold

    def _calc_progress(self, value: float) -> float:
        if self.is_upper_bound:
            if value == 0:
                progress = 0.0
            else:
                progress = value / self.threshold
        else:
            progress = self.threshold - value

        return progress

    @abstractmethod
    def evaluate(self) -> GoalEvaluation: ...

    @abstractmethod
    def has_been_reached(self) -> bool: ...

    @property
    @abstractmethod
    def goal_type_repr(self) -> str: ...

    @property
    @abstractmethod
    def goal_type(self) -> GoalType: ...

    def _filter_date_dataframe(self, data: pd.DataFrame) -> pd.DataFrame:
        if "date" not in data.columns:
            raise RuntimeError

        if self.temporal_type is TemporalType.MONTHLY:
            if self.month is None:
                raise RuntimeError
            month_start = date(self.year, self.month, 1)
            if self.month == 12:
                next_month_start = date(self.year + 1, 1, 1)
            else:
                next_month_start = date(self.year, self.month + 1, 1)

            return data[(data.date >= month_start) & (data.date < next_month_start)]
        elif self.temporal_type is TemporalType.YEARLY:
            year_begin = date(self.year, 1, 1)
            year_end = date(self.year, 12, 31)

            return data[(data.date >= year_begin) & (data.date <= year_end)]
        else:
            raise NotImplementedError

    def _apply_constraints(self, data: pd.DataFrame) -> pd.DataFrame:
        if self.constraints is None:
            return data

        mask = pd.Series(len(data) * [True])
        if "ride_type" in self.constraints.keys():
            mask = mask & data.ride_type.isin(self.constraints["ride_type"])

        if "bike" in self.constraints.keys():
            mask = mask & data.bike.isin(self.constraints["bike"])

        return data[mask]


@final
class RideGoal(Goal):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        if not is_acceptable_aggregation(GoalType.RIDE, self.aggregation_type):
            raise NotImplementedError(
                f"Aggregation {self.aggregation_type} is not supported for RideGoals"
            )

    def has_been_reached(self, data: pd.DataFrame) -> bool:
        """
        Checks the passed data against the gaol settings

        :param data: Dataframe with columns *date*, *distance*
        :return: Boolean value specifiying if the gaol has been reached
        """
        return self.evaluate(data).reached

    def evaluate(self, data: pd.DataFrame) -> GoalEvaluation:
        """Evaluate the goal gainst the passed data. Returns boolen flag and
        a numerical progress. The numberical progress is a number between 0 and 1
        (%) if the goal threshold is an upper_bound and the difference to the threshold
        if the threshold is a lower bound.

        :param data: Data to be evaluated
        :return: GoalEvaluation with boolean flag, current value, and progress
        """
        relevant_data = self._relevant_data(self._apply_constraints(data))
        if relevant_data.empty:
            return GoalEvaluation(False, 0, 0 if self.is_upper_bound else np.nan)

        curr_value = agg_ride_goal(relevant_data, self.aggregation_type)

        return GoalEvaluation(
            self._check(curr_value),
            curr_value,
            self._calc_progress(curr_value),
        )

    def _relevant_data(self, data: pd.DataFrame) -> pd.DataFrame:
        return self._filter_date_dataframe(data)

    @property
    def goal_type_repr(self) -> str:
        return f"{self.temporal_type.value}RideGoal"

    @property
    def goal_type(self) -> GoalType:
        return GoalType.RIDE


@final
class ManualGoal(Goal):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        if not is_acceptable_aggregation(GoalType.MANUAL, self.aggregation_type):
            raise NotImplementedError(
                f"Aggregation {self.aggregation_type} is not supported for ManualGoals"
            )

        if self.month is not None and self.month == 0:
            raise GoalSetupError(
                "Implicit monthly goals are not supported for manual goals"
            )

    def _get_relevant_data(self) -> float:
        return 0 if self.value is None else self.value

    def has_been_reached(self) -> bool:
        return self.evaluate().reached

    def evaluate(self) -> GoalEvaluation:
        aggregated_value = agg_manual_goal(
            self._get_relevant_data(), self.aggregation_type
        )

        return GoalEvaluation(
            self._check(aggregated_value),
            aggregated_value,
            self._calc_progress(aggregated_value),
        )

    @property
    def goal_type_repr(self) -> str:
        return f"{self.temporal_type.value}ManualGoal"

    @property
    def goal_type(self) -> GoalType:
        return GoalType.MANUAL


@final
class LocationGoal(Goal):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        if not is_acceptable_aggregation(GoalType.MANUAL, self.aggregation_type):
            raise NotImplementedError(
                f"Aggregation {self.aggregation_type} is not supported for ManualGoals"
            )

        if self.constraints is None or "id_location" not in self.constraints.keys():
            raise GoalSetupError(
                "Constraints must be set and contain *id_location* as key"
            )

        if not isinstance(self.constraints["id_location"], int):
            raise GoalSetupError("id_location constraint must be int")

        if "max_distance" in self.constraints:
            if not isinstance(self.constraints["max_distance"], (float, int)):
                raise GoalSetupError("max_distance constraint must be float or int")

    def has_been_reached(self, data: pd.DataFrame) -> bool:
        return self.evaluate(data).reached

    def evaluate(self, data: pd.DataFrame) -> GoalEvaluation:
        """Evaluate the goal gainst the passed location data.

        :param data: Dataframe with columns location_id, distance, ride_id, year,
            month, terrain_type, and bike_name
        :return: _description_
        """
        if self.constraints is None:
            raise RuntimeError

        if data.empty:
            return GoalEvaluation(False, 0, 0 if self.is_upper_bound else np.nan)

        mask = data.location_id == self.constraints["id_location"]
        max_distance: None | float = self.constraints.get("max_distance", None)  # type: ignore
        ride_types: None | list[str] = self.constraints.get("ride_type", None)  # type: ignore
        bikes: None | list[str] = self.constraints.get("bike", None)  # type: ignore
        if max_distance is not None:
            mask = mask & (data.distance <= max_distance)
        if ride_types is not None:
            mask = mask & data.ride_type.isin(ride_types)
        if bikes is not None:
            mask = mask & data.bike_name.isin(bikes)

        relevant_data = self._filter_date_dataframe(data[mask])
        if relevant_data.empty:
            return GoalEvaluation(False, 0, 0 if self.is_upper_bound else np.nan)

        aggregated_value = agg_location_goal(relevant_data, self.aggregation_type)

        return GoalEvaluation(
            self._check(aggregated_value),
            aggregated_value,
            self._calc_progress(aggregated_value),
        )

    @property
    def goal_type_repr(self) -> str:
        return f"{self.temporal_type.value}LocationGoal"

    @property
    def goal_type(self) -> GoalType:
        return GoalType.LOCATION


def format_goals_concise(goals: list[Goal]) -> list[ConciseGoal]:
    formatted_goals = []
    for goal in goals:
        formatted_goals.append(
            ConciseGoal(
                goal.name,
                goal.goal_type_repr,
                goal.aggregation_type.get_formatted_condition(
                    goal.threshold, goal.goal_type
                ),
                int(goal.reached),
            )
        )

    return formatted_goals
