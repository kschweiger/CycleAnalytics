import logging

from flask import Blueprint, current_app, flash, redirect, url_for
from geo_track_analyzer import ByteTrack
from werkzeug import Response

from cycle_analytics.database.model import DatabaseTrack, Ride, TrackLocationAssociation
from cycle_analytics.database.model import db as orm_db
from cycle_analytics.database.retriever import get_locations_for_track
from cycle_analytics.utils.track import check_location_in_track, get_enhanced_db_track

bp = Blueprint("track", __name__, url_prefix="/track")

logger = logging.getLogger(__name__)


@bp.route("enhance/<int:id_ride>/", methods=("GET", "POST"))
def enhance_track(id_ride: int) -> Response:
    logger.info("Running enhancement for latest track in id_ride %s", id_ride)
    ride = orm_db.get_or_404(Ride, id_ride)
    current_db_track = ride.database_track
    current_track = ride.track
    if current_track is None or current_db_track is None:
        flash(f"Ride {id_ride} has no track", "alert-warning")
        return redirect(url_for("ride.display", id_ride=id_ride))

    new_db_track = get_enhanced_db_track(current_track)
    if new_db_track is None:
        return redirect(url_for("ride.display", id_ride=id_ride))

    if current_db_track.is_enhanced:
        orm_db.session.delete(current_db_track)
        orm_db.session.commit()
        flash("Previous enhanced track deleted", "alert-warning")

    ride.tracks.append(new_db_track)
    orm_db.session.commit()
    flash("Track enhanced", "alert-success")
    return redirect(url_for("ride.display", id_ride=id_ride))


@bp.route("match_locations/<int:id_track>", methods=("GET", "POST"))
def match_locations(id_track: int) -> Response:
    max_distance = current_app.config.matching.distance
    database_track = orm_db.get_or_404(DatabaseTrack, id_track)

    track = ByteTrack(database_track.content)

    locations = get_locations_for_track(id_track)
    location_matches = check_location_in_track(
        track, locations, max_distance=max_distance
    )
    for loc, match in zip(locations, location_matches):
        logger.debug("Match: %s = %s", loc, match)
        if match:
            orm_db.session.add(
                TrackLocationAssociation(
                    track_id=database_track.id, location_id=loc.id, distance=100
                )
            )
            orm_db.session.commit()
            flash(
                f"Matched location '{loc.name}' @ "
                f"({loc.latitude:.4f},{loc.longitude:.4f}) to track {id_track}",
                "alert-success",
            )
    return redirect(url_for("landing_page"))
