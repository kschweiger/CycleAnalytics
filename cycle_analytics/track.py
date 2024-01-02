import logging
from datetime import datetime

from flask import Blueprint, current_app, flash, redirect, url_for
from track_analyzer import get_enhancer
from track_analyzer.exceptions import APIHealthCheckFailedError, APIResponseError
from werkzeug import Response

from cycle_analytics.database.converter import initialize_overviews
from cycle_analytics.database.model import DatabaseTrack, Ride
from cycle_analytics.database.model import db as orm_db

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

    try:
        enhancer = get_enhancer(current_app.config.external.track_enhancer.name)(
            url=current_app.config.external.track_enhancer.url,
            **current_app.config.external.track_enhancer.kwargs.to_dict(),
        )  # type: ignore
    except APIHealthCheckFailedError:
        logger.warning("Enhancer not available. Skipping elevation profile")
        flash("Track could not be enhanced - API not available", "alert-danger")
        return redirect(url_for("ride.display", id_ride=id_ride))
    try:
        enhancer.enhance_track(current_track.track, True)
    except APIResponseError:
        flash("Could not enhance track with elevation", "alert-danger")
        logger.error("Could not enhance track with elevation")
        return redirect(url_for("ride.display", id_ride=id_ride))

    new_db_track = DatabaseTrack(
        content=current_track.get_xml().encode(),
        added=datetime.now(),
        is_enhanced=True,
        overviews=initialize_overviews(current_track, None),
    )

    if current_db_track.is_enhanced:
        orm_db.session.delete(current_db_track)
        flash("Previous enhanced track deleted", "alert-warning")

    ride.tracks.append(new_db_track)
    orm_db.session.commit()
    flash("Track enhanced", "alert-success")
    return redirect(url_for("ride.display", id_ride=id_ride))
