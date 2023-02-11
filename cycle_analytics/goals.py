from abc import ABC, abstractmethod
from copy import copy
from datetime import date
from enum import Enum
from typing import Dict

import numpy as np
import pandas as pd
from flask import Blueprint, flash, render_template, request
from flask_wtf import FlaskForm
from wtforms import RadioField, SelectField
from wtforms.validators import DataRequired

from cycle_analytics.model import GoalDisplayData, GoalInfoData
from cycle_analytics.utils import get_month_mapping


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
    def __init__(self, **kwargs):
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
        if self.month == 12:
            next_month_start = date(self.year + 1, 1, 1)
        else:
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


class OverviewForm(FlaskForm):
    year = SelectField(
        "Year", validators=[DataRequired()], default=str(date.today().year), coerce=int
    )
    month = SelectField(
        "Month",
        validators=[DataRequired()],
        choices=[(i, get_month_mapping()[i]) for i in range(1, 13)],
        default=date.today().month,
        coerce=int,
    )
    active = RadioField(
        "Show active",
        choices=[(True, "Show active")],
        coerce=bool,
        validate_choice=False,
    )
    inactive = RadioField(
        "Show inactive",
        choices=[(True, "Show inactive")],
        coerce=bool,
        validate_choice=False,
    )


bp = Blueprint("goals", __name__, url_prefix="/goals")


@bp.route("/", methods=("GET", "POST"))
def overview():
    from cycle_analytics.queries import (
        get_rides_in_timeframe,
        load_goals,
        modify_goal_status,
    )

    if request.form.get("change_state_goal_id") is not None:
        id_to_update = int(request.form.get("change_state_goal_id"))
        status_value = request.form.get("change_state_value")
        modify_succ = modify_goal_status(
            id_to_update,
            status_value == "Activate",
        )
        if modify_succ:
            flash(
                f"Goal {id_to_update} has been {status_value.lower()}d",
                "alert-success",
            )
        else:
            flash(
                f"An error corrured with change state if goal {id_to_update}",
                "alert-danger",
            )

    form = OverviewForm()
    form.year.choices = ["2023", "2022"]

    month_mapping = get_month_mapping()

    today = date.today()

    load_year = today.year
    load_month = today.month

    load_active = True
    load_inactive = False
    if form.validate_on_submit():
        load_year = form.year.data
        load_month = form.month.data

        if form.active.data is not None:
            load_active = True
        else:
            load_active = False
        if form.inactive.data is not None:
            load_inactive = True
        else:
            load_inactive = False

    goals = load_goals(load_year, load_active, load_inactive)

    form.active.data = load_active if load_active else None
    form.inactive.data = load_inactive if load_inactive else None

    year_goals = [g for g in goals if g.month is None]
    month_goals = [g for g in goals if g.month == load_month]

    data = get_rides_in_timeframe(load_year)

    year_goal_displays = []
    month_goal_displays = []
    # TODO: Add update of has_been_reached column
    for goal in year_goals + month_goals:
        status, current_value, progress = goal.evaluate(data)
        goal_data = GoalDisplayData(
            goal_id=str(goal.id),
            info=GoalInfoData(
                name=goal.name,
                goal=goal.type.get_formatted_condition(goal.threshold),
                threshold=goal.threshold,
                value=round(current_value, 2)
                if isinstance(current_value, float)
                else current_value,
                progress=round(progress * 100) if goal.is_upper_bound else progress,
                reached=int(status),
                active=goal.active,
                description=goal.description,
            ),
            progress_bar=goal.is_upper_bound,
        )
        if goal in year_goals:
            year_goal_displays.append(goal_data)
        else:
            month_goal_displays.append(goal_data)

    return render_template(
        "goals.html",
        active_page="goals",
        overview_form=form,
        year=load_year,
        month=month_mapping[load_month],
        year_goal_displays=year_goal_displays,
        month_goal_displays=month_goal_displays,
    )
