import logging
from datetime import date

from data_organizer.db.exceptions import QueryReturnedNoData
from flask import render_template, request

from cycle_analytics.goals import YearlyGoal, format_goals_concise
from cycle_analytics.queries import (
    get_goal_years,
    get_last_ride,
    get_summary_data,
    get_years_in_database,
    load_goals,
)
from cycle_analytics.utils import get_month_mapping

logger = logging.getLogger(__name__)


def render_landing_page():
    logger.debug("Rendering landing page")
    print(request.form)
    # config = current_app.config
    date_today = date.today()
    # date_today = date(2022, 12, 31)
    last_ride_types = ["Any", "MTB"]
    last_ride_type_selected = "MTB"
    # TODO: Add POST requests for last ride
    last_ride = get_last_ride(last_ride_type_selected)

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
        goals_ = load_goals(goal_year_selected)
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
    goals = format_goals_concise(display_goals)

    summary_years = ["All"] + [str(y) for y in get_years_in_database()]
    summary_year_selected = date_today.year
    # TODO: Add POST requests for summary
    summary_data, summary_month = get_summary_data(
        summary_year_selected, date_today.year, date_today.month
    )

    # TEMP ---------- START ----------

    recent_events = [
        ("Broken chain", "Mechanical", date(2022, 11, 12)),
        ("Slipped on root", "Crash", date(2022, 12, 1)),
    ]

    recent_event_types = ["Any", "Mechanical", "Crash"]

    recent_event_selected = "Any"

    # goals = [("Goal1", "Yearly", "1250 km", 1), ("Goal2", "Monthly", "8 Rides", 0)]
    # TEMP ---------- END ----------

    return render_template(
        "landing_page.html",
        active_page="home",
        last_ride=last_ride,
        last_ride_types=last_ride_types,
        last_ride_type_selected=last_ride_type_selected,
        recent_events=recent_events,
        recent_event_types=recent_event_types,
        recent_event_selected=recent_event_selected,
        goal_months=goal_months,
        goal_month_selected=goal_month_selected,
        goal_years=goal_years,
        goal_year_selected=goal_year_selected,
        goals=goals,
        summary_years=summary_years,
        summary_year_selected=summary_year_selected,
        summary_data=summary_data,
        summary_month=summary_month,
    )
