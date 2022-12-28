from datetime import date
from flask import current_app, render_template

from cycle_analytics.model import LastRide


def render_landing_page():
    config = current_app.config

    # TEMP ---------- START ----------
    last_ride = LastRide(
        date=date(2022, 12, 1),
        data={
            "Distance [km]": "22.2",
            "Duration": "01:15:00",
            "Avg. Velocity [km/h]": "15.5",
        },
    )
    last_ride_types = ["Any", "MTB"]
    last_ride_type_selected = "MTB"

    recent_events = [
        ("Broken chain", "Mechanical", date(2022, 11, 12)),
        ("Slipped on root", "Crash", date(2022, 12, 1)),
    ]

    recent_event_types = ["Any", "Mechanical", "Crash"]

    recent_event_selected = "Any"

    summary_years = ["All", "2022"]
    summary_year_selected = "2022"
    summary_data = [
        ("Total Distance [km]", "1000"),
        ("Total Ride time ", "3 days 11:00:00"),
        ("Number of rides", "60"),
        ("Avg. distance [km]", "20.2"),
        ("Avg. ride duration", "01:10:11"),
    ]

    summary_month = [
        ("Distance [km]", "20", 1),
        ("Ride time", "01:22:22", 0),
        ("Rides", "2", -1),
    ]

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


def get_last_ride(ride_type: str):
    ...
