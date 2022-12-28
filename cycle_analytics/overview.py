from datetime import date
from flask import Blueprint, render_template

from cycle_analytics.db import get_db


bp = Blueprint("overview", __name__, url_prefix="/overview")


@bp.route("/", methods=("GET", "POST"))
def main():

    db = get_db()

    years = ["All"]
    selected_year = date.today().year

    table_headings = []
    table_data = []

    # TODO: Load Data

    # TEMP ---------- START ----------
    # TEMP Pseudo Data
    table_headings = ["Date", "Start Time", "Ride Time", "Total Time", "Distance [km]"]
    table_data = [
        (
            (
                "2022-12-01",
                "#",
            ),
            "13:00:00",
            "01:00:00",
            "01:10:00",
            "22.2",
        ),
    ]
    years = ["All", "2022"]
    # TEMP ---------- END ----------

    return render_template(
        "overview.html",
        active_page="overview",
        year_selected=str(selected_year),
        years=years,
        table_data=(table_headings, table_data),
    )


@bp.route("/heatmap", methods=("GET", "POST"))
def heatmap():
    return render_template("visualizations/heatmap.html", active_page="overview")
