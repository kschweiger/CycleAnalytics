import logging

from flask import (
    Blueprint,
    Response,
    current_app,
    flash,
    redirect,
    render_template,
    url_for,
)
from sqlalchemy import select

from cycle_analytics.database.model import (
    DatabaseLocation,
    TrackLocationAssociation,
    db,
)
from cycle_analytics.database.retriever import get_locations
from cycle_analytics.utils.base import convert_locations_to_markers
from cycle_analytics.utils.track import find_possible_tracks_for_location

logger = logging.getLogger(__name__)


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


@bp.route("/match_tracks/<int:id_location>", methods=("GET", "POST"))
def match_tracks(id_location: int) -> Response:
    max_distance = current_app.config.matching.distance
    loc = db.session.get(DatabaseLocation, id_location)
    if loc is None:
        flash(f"Location with id {id_location} is no valid location", "alert-danger")
        return redirect(url_for("locations.overview"))  # type: ignore

    track_ids = find_possible_tracks_for_location(
        loc.latitude, loc.longitude, max_distance
    )

    for id_track in track_ids:
        existing_assiciation = db.session.execute(
            select(TrackLocationAssociation)
            .filter(TrackLocationAssociation.track_id == id_track)
            .filter(TrackLocationAssociation.location_id == loc.id)
        ).all()

        if len(existing_assiciation) > 0:
            logger.debug(
                "Track %s already has a association to location %s", id_track, loc.id
            )
            continue

        db.session.add(
            TrackLocationAssociation(
                track_id=id_track, location_id=loc.id, distance=max_distance
            )
        )
        db.session.commit()
        flash(
            f"Matched location '{loc.name}' @ "
            f"({loc.latitude:.4f},{loc.longitude:.4f}) to track {id_track}",
            "alert-success",
        )

    return redirect(url_for("locations.overview"))  # type: ignore
