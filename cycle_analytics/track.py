import logging

from flask import Blueprint, current_app, redirect, url_for
from werkzeug import Response

from cycle_analytics.queries import get_track_data, ride_track_id
from cycle_analytics.utils.track import enhance_and_insert_track

bp = Blueprint("track", __name__, url_prefix="/track")

logger = logging.getLogger(__name__)


@bp.route("enhance/<int:id_ride>/<int:id_track>/", methods=("GET", "POST"))
def enhance_track(id_ride: int, id_track: int) -> Response:
    logger.info("Running enhancement for raw track %s of id_ride", id_track, id_ride)
    # Load data of raw track
    data = get_track_data(
        id_track,
        current_app.config.tables_as_settings[
            current_app.config.defaults.raw_track_table
        ].name,
    )
    # Check if there is an enhanced track for id_ride. If yes, replace
    enhance_id = ride_track_id(
        id_ride,
        current_app.config.tables_as_settings[
            current_app.config.defaults.track_table
        ].name,
    )

    enhance_and_insert_track(data=data, id_ride=id_ride, enhance_id=enhance_id)

    return redirect(url_for("ride.display", id_ride=id_ride))
