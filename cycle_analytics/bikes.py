import logging

from flask import Blueprint, render_template

from cycle_analytics.queries import get_agg_data_for_bike, get_full_bike_date

logger = logging.getLogger(__name__)


bp = Blueprint("bike", __name__, url_prefix="/bike")


@bp.route("/<bike_name>/", methods=("GET", "POST"))
def show(bike_name: str):
    bike = get_full_bike_date(bike_name)

    agg_data = get_agg_data_for_bike(bike_name)

    return render_template(
        "show_bike.html", active_page="bike", bike=bike, agg_data=agg_data
    )
