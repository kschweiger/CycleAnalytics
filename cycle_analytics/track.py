import logging

from flask import Blueprint, flash, redirect, url_for
from werkzeug import Response

from cycle_analytics.database.model import Ride
from cycle_analytics.database.model import db as orm_db
from cycle_analytics.utils.track import get_enhanced_db_track

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
        flash("Previous enhanced track deleted", "alert-warning")

    ride.tracks.append(new_db_track)
    orm_db.session.commit()
    flash("Track enhanced", "alert-success")
    return redirect(url_for("ride.display", id_ride=id_ride))
