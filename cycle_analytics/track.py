import json
import logging
import re

import pandas as pd
import plotly
from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from geo_track_analyzer import ByteTrack, Track
from geo_track_analyzer.utils.track import extract_track_data_for_plot
from geo_track_analyzer.visualize import plot_tracks_on_map
from werkzeug import Response

from cycle_analytics.database.model import DatabaseTrack, Ride, TrackLocationAssociation
from cycle_analytics.database.model import db as orm_db
from cycle_analytics.database.retriever import (
    get_locations_for_track,
    get_rides_with_tracks,
)
from cycle_analytics.utils.forms import get_track_from_file_storage
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
    _match_locations(new_db_track)
    return redirect(url_for("ride.display", id_ride=id_ride))


def _match_locations(database_track: DatabaseTrack) -> None:
    max_distance = current_app.config.matching.distance
    track = ByteTrack(database_track.content)

    locations = get_locations_for_track(database_track.id)
    location_matches = check_location_in_track(
        track, locations, max_distance=max_distance
    )
    for loc, (match, distance) in zip(locations, location_matches):
        logger.debug("Match: %s = %s", loc, match)
        if match:
            orm_db.session.add(
                TrackLocationAssociation(
                    track_id=database_track.id,
                    location_id=loc.id,
                    distance=distance,
                )
            )
            orm_db.session.commit()
            flash(
                f"Matched location '{loc.name}' @ "
                f"({loc.latitude:.4f},{loc.longitude:.4f}) to "
                f"track {database_track.id}",
                "alert-success",
            )


@bp.route("match_locations/<int:id_track>", methods=("GET", "POST"))
def match_locations(id_track: int) -> Response:
    database_track = orm_db.get_or_404(DatabaseTrack, id_track)
    _match_locations(database_track)
    return redirect(url_for("landing_page"))


@bp.route("compare/", methods=("GET", "POST"))
def compare() -> str | Response:
    map_plot = None
    ride_data_ = get_rides_with_tracks()
    ride_data: list[tuple[str, str]] = []
    for data in ride_data_:
        ride_id, ride_date, ride_distance, bike = data
        ride_data.append(
            (
                f"{ride_date.isoformat()} - ID: {ride_id}",
                f"Bike: {bike} | Distance: {ride_distance:.2f}",
            )
        )
    if request.method == "POST":
        choice_pattern = r"^\d{4}-\d{2}-\d{2} - ID: \d+$"
        id_pattern = r"\bID: (\d+)\b"
        ride_choices = request.form.getlist("track_choice")
        ride_tracks: list[Track] = []
        valid_form = True

        added_choices = []
        for ride in ride_choices:
            if ride in added_choices:
                flash("Same ride passed mutliple times", "alert-danger")
                valid_form = False
                break

            if not bool(re.match(choice_pattern, ride)):
                flash(f"Invalid ride choice: {ride}", "alert-danger")
                valid_form = False
                break

            match = re.search(id_pattern, ride)
            if match:
                ride_id = int(match.group(1))
                this_track = orm_db.get_or_404(Ride, ride_id).track
                if this_track is None:
                    flash(f"Could not load track for {ride}", "alert-danger")
                    valid_form = False
                    break
                ride_tracks.append(this_track)
                added_choices.append(ride)
            else:
                flash(f"Could not extract id from {ride}", "alert-danger")
                valid_form = False
                break

        files = request.files.getlist("compare_file")
        file_tracks: list[Track] = []
        added_file_names = []
        for file in files:
            if file.filename in added_file_names:
                flash("Same file passed mutliple times", "alert-danger")
                valid_form = False
                break
            file_tracks.append(get_track_from_file_storage(file))
            added_file_names.append(file.filename)

        if valid_form and (len(ride_tracks) + len(file_tracks)) > 1:
            track_names: list[str] = []
            track_datas: list[pd.DataFrame] = []
            for i, track in enumerate(file_tracks):
                track_names.append(f"File {i}")
                track_datas.append(extract_track_data_for_plot(track, "foo", ["foo"]))
            for choice, track in zip(ride_choices, ride_tracks):
                track_names.append(choice)
                track_datas.append(extract_track_data_for_plot(track, "foo", ["foo"]))

            fig = plot_tracks_on_map(track_datas, track_names)
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=0, r=0, b=0, t=0, pad=0),
            )

            map_plot = json.dumps(
                fig,
                cls=plotly.utils.PlotlyJSONEncoder,
            )

    return render_template(
        "compare_tracks.html",
        active_page="utils_compare",
        ride_data=ride_data,
        map_plot=map_plot,
    )
