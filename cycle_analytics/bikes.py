import logging

from data_organizer.db.exceptions import QueryReturnedNoData
from flask import Blueprint, flash, redirect, render_template, url_for
from werkzeug import Response

from cycle_analytics.queries import get_agg_data_for_bike, get_full_bike_date

logger = logging.getLogger(__name__)


bp = Blueprint("bike", __name__, url_prefix="/bike")


@bp.route("/<bike_name>/", methods=("GET", "POST"))
def show(bike_name: str) -> str | Response:
    try:
        bike = get_full_bike_date(bike_name)
    except QueryReturnedNoData:
        flash(
            f"<b>{bike_name}</b> is no valid bike. You can add it via "
            f"<a href='{url_for('adders.add_bike')}'>this form</a>",
            "alert-danger",
        )
        return redirect("/")

    agg_data = get_agg_data_for_bike(bike_name)

    return render_template(
        "show_bike.html", active_page="bike", bike=bike, agg_data=agg_data
    )
