from datetime import date

import pandas as pd
from flask import Blueprint, current_app, render_template, request

from cycle_analytics.plotting import per_month_overview_plots
from cycle_analytics.queries import get_rides_in_timeframe, get_years_in_database
from cycle_analytics.utils import get_nice_timedelta_isoformat

bp = Blueprint("overview", __name__, url_prefix="/overview")


@bp.route("/", methods=("GET", "POST"))
def main():
    years = ["All"] + [str(y) for y in get_years_in_database()]
    selected_year = date.today().year

    if request.method == "POST":
        selected_year = request.form.get("year")

    table_headings = [
        "Date",
        "Ride Time",
        "Total Time",
        "Distance [km]",
        "Avg. Velocity [km/h]",
        "Uphill [m]",
        "Downhill [m]",
    ]
    table_data = []

    rides = get_rides_in_timeframe(selected_year)
    for rcrd in rides.to_dict("records"):
        # thumbnails = get_thumbnails_for_id(rcrd["id_ride"])
        table_data.append(
            (
                (rcrd["date"].isoformat(), "#"),
                ""
                if pd.isnull(rcrd["ride_time"])
                else get_nice_timedelta_isoformat(rcrd["ride_time"].isoformat()),
                get_nice_timedelta_isoformat(rcrd["total_time"].isoformat()),
                rcrd["distance"],
                ""
                if pd.isnull(rcrd["avg_velocity_kmh"])
                else round(rcrd["avg_velocity_kmh"], 2),
                ""
                if pd.isnull(rcrd["uphill_elevation"])
                else round(rcrd["uphill_elevation"], 2),
                ""
                if pd.isnull(rcrd["downhill_elevation"])
                else round(rcrd["downhill_elevation"], 2),
            )
        )

    plots = per_month_overview_plots(
        rides,
        [
            ("id_ride", "count", "Number of rides per Month", "Count", False),
            ("distance", "sum", "Distance per Month", "Distance [km]", False),
            (
                "distance",
                "avg",
                "Average ride distance per Month",
                "Distance [km]",
                False,
            ),
            (
                "distance",
                "sum",
                "Cumulative distance per Month",
                "Distance [km]",
                True,
            ),
        ],
        width=1200,
        color_sequence=current_app.config.style.color_sequence,
    )

    return render_template(
        "overview.html",
        active_page="overview",
        year_selected=str(selected_year),
        years=years,
        table_data=(table_headings, table_data),
        plots=plots,
    )


@bp.route("/heatmap", methods=("GET", "POST"))
def heatmap():
    return render_template("visualizations/heatmap.html", active_page="overview")
