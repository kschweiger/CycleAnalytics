import logging
from datetime import date

from flask import render_template

from cycle_analytics.queries import (
    get_last_ride,
    get_summary_data,
    get_years_in_database,
)

logger = logging.getLogger(__name__)


def render_landing_page():
    logger.debug("Rendering landing page")
    # config = current_app.config

    last_ride_types = ["Any", "MTB"]
    last_ride_type_selected = "MTB"
    # TODO: Add POST requests for last ride
    last_ride = get_last_ride(last_ride_type_selected)

    summary_years = ["All"] + [str(y) for y in get_years_in_database()]
    date_today = date.today()
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
        summary_years=summary_years,
        summary_year_selected=summary_year_selected,
        summary_data=summary_data,
        summary_month=summary_month,
    )
