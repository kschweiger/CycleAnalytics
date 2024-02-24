import logging
from datetime import date

from flask import Blueprint, flash, render_template, request
from flask_wtf import FlaskForm
from wtforms import RadioField, SelectField
from wtforms.validators import DataRequired

from cycle_analytics.model.base import GoalDisplayData, GoalInfoData
from cycle_analytics.model.goal import ManualGoal, RideGoal
from cycle_analytics.utils import get_month_mapping
from cycle_analytics.utils.base import unwrap

logger = logging.getLogger(__name__)


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
def overview() -> str:
    from cycle_analytics.database.converter import convert_rides_to_df
    from cycle_analytics.database.modifier import (
        modify_goal_status,
        modify_manual_goal_value_count,
    )
    from cycle_analytics.database.retriever import (
        get_goal_years_in_database,
        get_rides_in_timeframe,
        load_goals,
    )

    validate_overview_form = True

    if request.form.get("change_state_goal_id") is not None:
        validate_overview_form = False
        id_to_update = int(unwrap(request.form.get("change_state_goal_id")))
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

    if request.form.get("value_manua_goal_id") is not None:
        validate_overview_form = False
        id_to_update = int(unwrap(request.form.get("value_manua_goal_id")))
        change: str = unwrap(request.form.get("change_value"))
        if change == "increase":
            logger.debug("Increasing value of goal with id %s", id_to_update)
            modify_succ = modify_manual_goal_value_count(id_to_update, "increase")
        elif change == "decrease":
            logger.debug("Decrease value of goal with id %s", id_to_update)
            modify_succ = modify_manual_goal_value_count(id_to_update, "decrease")
        else:
            raise ValueError(f"Value {change} is not supported")

    form = OverviewForm()
    form.year.choices = [(y, str(y)) for y in get_goal_years_in_database()]

    month_mapping = get_month_mapping()

    today = date.today()

    load_year = today.year
    load_month = today.month

    load_active = True
    load_inactive = False
    if form.validate_on_submit() and validate_overview_form:
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
    logger.debug(f"load_goals {load_year=}, {load_active=}, {load_inactive=})")
    goals = load_goals(load_year, load_active, load_inactive)
    logger.debug("Loaded %s goals", len(goals))
    form.active.data = load_active if load_active else None
    form.inactive.data = load_inactive if load_inactive else None

    year_goals = [g for g in goals if g.month is None]
    month_goals = [g for g in goals if g.month == load_month]

    data = convert_rides_to_df(get_rides_in_timeframe(load_year))

    year_goal_displays = []
    month_goal_displays = []
    # TODO: Add update of has_been_reached column
    for goal in year_goals + month_goals:
        is_manual = False
        decreasable = False
        if isinstance(goal, RideGoal):
            evaluation = goal.evaluate(data)
        elif isinstance(goal, ManualGoal):
            evaluation = goal.evaluate()
            is_manual = True
            decreasable = True
            if goal.value is None or goal.value < 1:
                decreasable = False
        # status, current_value, progress = goal.evaluate(data)
        goal_data = GoalDisplayData(
            goal_id=str(goal.id),
            info=GoalInfoData(
                name=goal.name,
                goal=goal.aggregation_type.get_formatted_condition(
                    goal.threshold, goal.goal_type
                ),
                threshold=goal.threshold,
                value=round(evaluation.current, 2)
                if isinstance(evaluation.current, float)
                else evaluation.current,
                progress=round(evaluation.progress * 100)
                if goal.is_upper_bound
                else evaluation.progress,
                reached=int(evaluation.reached),
                active=goal.active,
                description=goal.description,
                is_manual=is_manual,
                decreasable=decreasable,
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
