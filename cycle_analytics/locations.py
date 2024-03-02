from flask import Blueprint, Response, render_template

from cycle_analytics.database.retriever import get_locations
from cycle_analytics.model.base import MapMarker

bp = Blueprint("locations", __name__, url_prefix="/locations")


@bp.route("/", methods=("GET", "POST"))
def overview() -> str | Response:
    location_markers = []
    for location in get_locations():
        print(location)
        text = f"<b>{location.name}</b>"
        if location.description:
            text += f": {location.description}"
        location_markers.append(
            MapMarker(
                latitude=location.latitude,
                longitude=location.longitude,
                popup_text=text,
                color="blue",
                color_idx=0,
            )
        )

    return render_template(
        "locations.html",
        active_page="locations",
        location_markers=location_markers,
    )
