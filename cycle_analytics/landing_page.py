import logging
from datetime import date

from data_organizer.db.exceptions import QueryReturnedNoData
from flask import current_app, render_template, request

from cycle_analytics.goals import YearlyGoal, format_goals_concise
from cycle_analytics.queries import (
    get_goal_years,
    get_last_ride,
    get_recent_events,
    get_rides_in_timeframe,
    get_summary_data,
    get_years_in_database,
    load_goals,
)
from cycle_analytics.utils import get_month_mapping

logger = logging.getLogger(__name__)


def render_landing_page():
    logger.debug("Rendering landing page")
    config = current_app.config
    date_today = date.today()

    # --------------------- LAST RIDES ---------------------
    last_ride_types = ["Any"] + config.adders.ride.type_choices
    last_ride_type_selected = config.landing_page.last_ride.default_type
    if request.method == "POST" and request.form.get("form_last_ride_type") is not None:
        last_ride_type_selected = request.form.get("form_last_ride_type")

    last_ride = get_last_ride(
        None if last_ride_type_selected == "Any" else last_ride_type_selected
    )

    # --------------------- RECENT EVENTS ---------------------
    recent_event_type_selected = "All"
    recent_event_types = ["All"] + config.adders.event.type_choices
    if (
        request.method == "POST"
        and request.form.get("form_recent_event_type") is not None
    ):
        recent_event_type_selected = request.form.get("form_recent_event_type")

    events = get_recent_events(
        config.landing_page.events.n_max_recent,
        None if recent_event_type_selected == "All" else recent_event_type_selected,
    )

    recent_events = []

    for event in events:
        recent_events.append(
            (
                event["short_description"],
                event["event_type"],
                event["date"],
            )
        )

    # --------------------- GOALS ---------------------
    goal_years = [
        str(g) for g in sorted(get_goal_years() + [date_today.year], reverse=True)
    ]
    month_mapping = get_month_mapping()
    goal_year_selected = str(date_today.year)
    goal_month_selected = month_mapping[date_today.month]

    if request.method == "POST" and request.form.get("form_goals_year") is not None:
        goal_year_selected = request.form.get("form_goals_year")
        goal_month_selected = request.form.get("form_goals_month")

    inv_month_mapping = {value: key for key, value in month_mapping.items()}
    goal_months = [month_mapping[i] for i in range(1, 13)]

    try:
        goals_ = load_goals(goal_year_selected, True, False)
    except QueryReturnedNoData:
        goals_ = []

    display_goals = [
        goal
        for goal in goals_
        if (
            isinstance(goal, YearlyGoal)
            or goal.month == inv_month_mapping[goal_month_selected]
        )
    ]

    # -----------------------------------------------------------------------------
    # TODO: Check if this takes too long with more data. Maybe add an update button
    data = get_rides_in_timeframe(goal_year_selected)
    for goal in display_goals:
        reached, _, _ = goal.evaluate(data)
        goal.reached = reached
    # -----------------------------------------------------------------------------

    goals = format_goals_concise(display_goals)

    # --------------------- SUMMARY ---------------------
    summary_years = ["All"] + [str(y) for y in get_years_in_database()]
    summary_year_selected = str(date_today.year)
    summary_ride_types = ["Any"] + config.adders.ride.type_choices
    summary_ride_type_selected = config.landing_page.summary.default_type
    if (
        request.method == "POST"
        and request.form.get("form_summary_ride_type") is not None
    ):
        summary_year_selected = request.form.get("form_summary_year")
        summary_ride_type_selected = request.form.get("form_summary_ride_type")

    summary_data, summary_month = get_summary_data(
        summary_year_selected,
        date_today.year,
        date_today.month,
        summary_ride_type_selected,
    )
    return render_template(
        "landing_page.html",
        active_page="home",
        last_ride=last_ride,
        last_ride_types=last_ride_types,
        last_ride_type_selected=last_ride_type_selected,
        recent_events=recent_events,
        recent_event_types=recent_event_types,
        recent_event_type_selected=recent_event_type_selected,
        goal_months=goal_months,
        goal_month_selected=goal_month_selected,
        goal_years=goal_years,
        goal_year_selected=goal_year_selected,
        goals=goals,
        summary_years=summary_years,
        summary_year_selected=summary_year_selected,
        summary_ride_types=summary_ride_types,
        summary_ride_type_selected=summary_ride_type_selected,
        summary_data=summary_data,
        summary_month=summary_month,
    )
