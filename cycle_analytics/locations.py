from flask import Blueprint, Response, flash, redirect, render_template, url_for

from cycle_analytics.database.model import DatabaseLocation, db
from cycle_analytics.database.retriever import get_locations
from cycle_analytics.utils.base import convert_locations_to_markers

bp = Blueprint("locations", __name__, url_prefix="/locations")


@bp.route("/", methods=("GET", "POST"))
def overview() -> str | Response:
    location_markers = convert_locations_to_markers(get_locations(), True)

    return render_template(
        "locations.html",
        active_page="locations",
        location_markers=location_markers,
    )


@bp.route("/delete/<int:id_location>", methods=["GET"])
def delete_location(id_location: int) -> Response:
    loc = db.session.get(DatabaseLocation, id_location)
    if loc is None:
        flash(f"Location with id {id_location} is no valid location", "alert-danger")
        return redirect(url_for("locations.overview"))  # type: ignore
    db.session.delete(loc)
    db.session.commit()
    flash(f"Location {id_location} deleted", "alert-success")
    return redirect(url_for("locations.overview"))  # type: ignore
