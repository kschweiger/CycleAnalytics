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
    Ride,
    TrackLocationAssociation,
    db,
    ride_track,
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


@bp.route("/show/<int:id_location>", methods=["GET", "POST"])
def show(id_location: int) -> str | Response:
    location = db.get_or_404(DatabaseLocation, id_location)

    associations = db.session.execute(
        select(TrackLocationAssociation).filter(
            TrackLocationAssociation.location_id == id_location
        )
    ).scalars()

    contained_in_rides = []
    for association in associations:
        rel_ride_track = (
            db.session.query(ride_track)
            .filter_by(track_id=association.track_id)
            .first()
        )
        if rel_ride_track is None:
            continue
        id_ride, _ = rel_ride_track
        ride = db.get_or_404(Ride, id_ride)
        contained_in_rides.append(
            (
                (ride.id, ride.ride_date),
                ride.total_duration,
                ride.terrain_type,
                f"{ride.distance:.2f}",
                f"{association.distance:.2f}",
            )
        )
    contained_ride_table = (
        [
            "Date",
            "Duration",
            "Ride Type",
            "Ride distance [km]",
            "Location distance from track [m]",
        ],
        contained_in_rides,
    )

    return render_template(
        "locations/show.html",
        active_page="locations",
        location=location,
        contained_ride_table=contained_ride_table,
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


def _match_location_to_tracks(id_location: int) -> None:
    max_distance = current_app.config.matching.distance
    loc = db.session.get(DatabaseLocation, id_location)
    if loc is None:
        flash(f"Location with id {id_location} is no valid location", "alert-danger")
        return

    tracks = find_possible_tracks_for_location(
        loc.latitude, loc.longitude, max_distance
    )

    for id_track, distance in tracks:
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
                track_id=id_track, location_id=loc.id, distance=distance
            )
        )
        db.session.commit()
        flash(
            f"Matched location '{loc.name}' @ "
            f"({loc.latitude:.4f},{loc.longitude:.4f}) to track {id_track}",
            "alert-success",
        )


@bp.route("/match_tracks/<int:id_location>", methods=("GET", "POST"))
def match_tracks(id_location: int) -> Response:
    _match_location_to_tracks(id_location)
    return redirect(url_for("locations.overview"))  # type: ignore
