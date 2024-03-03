from flask import Blueprint, Response, render_template

from cycle_analytics.database.retriever import get_locations
from cycle_analytics.utils.base import convert_locations_to_merkers

bp = Blueprint("locations", __name__, url_prefix="/locations")


@bp.route("/", methods=("GET", "POST"))
def overview() -> str | Response:
    location_markers = convert_locations_to_merkers(get_locations())

    return render_template(
        "locations.html",
        active_page="locations",
        location_markers=location_markers,
    )
