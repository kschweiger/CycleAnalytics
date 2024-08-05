import logging
from datetime import date

from flask import Blueprint, flash, render_template, request
from flask_wtf import FlaskForm
from wtforms import RadioField, SelectField
from wtforms.validators import DataRequired

from cycle_analytics.database.converter import convert_ride_overview_container_to_df
from cycle_analytics.database.modifier import update_manual_goal_value
from cycle_analytics.database.retriever import (
    get_overview,
    resolve_track_location_association,
)
from cycle_analytics.model.base import GoalDisplayData, GoalInfoData, ManualGoalSetting
from cycle_analytics.model.goal import (
    AggregationType,
    LocationGoal,
    ManualGoal,
    RideGoal,
)
from cycle_analytics.utils import get_month_mapping
from cycle_analytics.utils.base import format_description, unwrap

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
    from cycle_analytics.database.modifier import (
        modify_goal_status,
        modify_manual_goal_value_count,
    )
    from cycle_analytics.database.retriever import (
        get_goal_years_in_database,
        load_goals,
    )

    validate_overview_form = True

    # ~~~~~~~~ Switch a goal between active and inactive ~~~~~~~~~~~~~~~~~~
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

    # ~~~~~~~~~ Deal with manual goal modifications ~~~~~~~~~~~~
    if request.form.get("value_manua_goal_id") is not None:
        validate_overview_form = False
        id_to_update = int(unwrap(request.form.get("value_manua_goal_id")))

        error = f"An error corrured with change state if goal {id_to_update}"
        modify_succ = False

        change: str = unwrap(request.form.get("change_value"))
        if change == "increase":
            logger.debug("Increasing value of goal with id %s", id_to_update)
            modify_succ = modify_manual_goal_value_count(id_to_update, "increase")
        elif change == "decrease":
            logger.debug("Decrease value of goal with id %s", id_to_update)
            modify_succ = modify_manual_goal_value_count(id_to_update, "decrease")
        else:
            logger.debug("Updating value of %s to %s", id_to_update, change)
            try:
                _change = float(change)
            except ValueError:
                error = f"Passed value {change} is not valid. Pass a number"
            else:
                modify_succ = update_manual_goal_value(id_to_update, _change)

        if modify_succ:
            flash(f"Goal {id_to_update} has been updated", "alert-success")
        else:
            flash(error, "alert-danger")

    today = date.today()

    load_year = today.year
    load_month = today.month

    form = OverviewForm()
    goal_years_in_db = get_goal_years_in_database()
    if today.year not in goal_years_in_db:
        goal_years_in_db.append(today.year)

    form.year.choices = [(y, str(y)) for y in sorted(goal_years_in_db, reverse=True)]

    month_mapping = get_month_mapping()

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

    data = convert_ride_overview_container_to_df(get_overview(load_year))
    data_location = resolve_track_location_association(str(load_year))
    year_goal_displays = []
    month_goal_displays = []
    # TODO: Add update of has_been_reached column
    for goal in year_goals + month_goals:
        manual_setting = None
        if isinstance(goal, RideGoal):
            evaluation = goal.evaluate(data)
        elif isinstance(goal, ManualGoal):
            manual_setting = ManualGoalSetting(
                steps=False,
                decreasable=False,
            )
            evaluation = goal.evaluate()
            if goal.aggregation_type in [AggregationType.COUNT]:
                manual_setting.steps = True
                manual_setting.decreasable = True
                if goal.value is None or goal.value < 1:
                    manual_setting.decreasable = False
        elif isinstance(goal, LocationGoal):
            evaluation = goal.evaluate(data_location)
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
                description=None
                if goal.description is None
                else format_description(goal.description),
                manual_setting=manual_setting,
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
