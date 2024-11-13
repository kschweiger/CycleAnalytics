import hashlib
import json
import logging
import re
from datetime import timedelta
from io import BytesIO

import pandas as pd
import plotly
from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_wtf import FlaskForm
from geo_track_analyzer import ByteTrack, Track
from geo_track_analyzer.utils.track import extract_track_data_for_plot
from geo_track_analyzer.visualize import plot_tracks_on_map
from werkzeug import Response
from wtforms import HiddenField
from wtforms.validators import DataRequired

from cycle_analytics.database.converter import initialize_overviews
from cycle_analytics.database.modifier import (
    update_track_content,
    update_track_overview,
)

from .cache import cache
from .database.model import DatabaseTrack, Ride, TrackLocationAssociation
from .database.model import db as orm_db
from .database.retriever import (
    get_locations_for_track,
    get_ride_for_track,
    get_rides_with_tracks,
)
from .forms import TrackUploadForm
from .model.base import MapData, MapPathData
from .utils.base import format_timedelta, unwrap
from .utils.forms import get_track_from_file_storage, get_track_from_wtf_form
from .utils.track import check_location_in_track, get_enhanced_db_track

bp = Blueprint("track", __name__, url_prefix="/track")

logger = logging.getLogger(__name__)


class TrackTrimForm(FlaskForm):
    orig_file_name = HiddenField("Original File Name", validators=[DataRequired()])
    cache_key = HiddenField("Cache Key", validators=[DataRequired()])
    start_idx = HiddenField("Start Index", validators=[DataRequired()])
    end_idx = HiddenField("End Index", validators=[DataRequired()])


class DatabaseTrackTrimForm(FlaskForm):
    track_id = HiddenField("Track ID", validators=[DataRequired()])
    start_idx = HiddenField("Start Index", validators=[DataRequired()])
    end_idx = HiddenField("End Index", validators=[DataRequired()])


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


def _get_map_data(track: Track) -> tuple[MapData, int]:
    track_segment_data = track.get_track_data()
    lats = track_segment_data.latitude.to_list()
    n_points = len(lats)
    lats = ",".join([str(l) for l in lats])  # noqa: E741
    longs = track_segment_data.longitude.to_list()
    longs = ",".join([str(l) for l in longs])  # noqa: E741
    paths = [MapPathData(latitudes=lats, longitudes=longs)]
    return MapData(paths=paths), n_points


@bp.route("trim/", methods=("GET", "POST"))
def trim() -> str | Response:
    _track_id = request.args.get("track_id", None)
    track_id = None if _track_id is None else int(_track_id)

    state = "empty"
    map_data = None
    form = TrackUploadForm()
    trim_form = TrackTrimForm()
    trim_database_form = DatabaseTrackTrimForm()

    track_cache_timeout_seconds = 60 * 10
    n_points = 1000
    if track_id is not None and not trim_database_form.validate_on_submit():
        state = "track-loaded"
        db_track = orm_db.get_or_404(DatabaseTrack, track_id)
        track = ByteTrack(db_track.content)
        map_data, n_points = _get_map_data(track)
        trim_database_form.track_id.data = track_id
        trim_database_form.start_idx.data = 0
        trim_database_form.end_idx.data = len(map_data.paths[0].latitudes) - 1
    if form.validate_on_submit():
        try:
            track = get_track_from_wtf_form(form, "track")
        except RuntimeError as e:
            flash(f"File could not be loaded: {e}", "alert-danger")
        else:
            state = "track-loaded"

            map_data, n_points = _get_map_data(track)

            file_name = form.track.data.filename
            assert isinstance(file_name, str)

            track_data = track.get_xml().encode()
            cache_key = hashlib.sha256(file_name.encode()).hexdigest()

            cache.set(
                cache_key,
                track_data,
                timeout=track_cache_timeout_seconds,
            )
            trim_form.start_idx.data = 0
            trim_form.end_idx.data = len(map_data.paths[0].latitudes) - 1
            trim_form.cache_key.data = cache_key
            trim_form.orig_file_name.data = ".".join(file_name.split(".")[0:-1])

    if trim_form.validate_on_submit():
        logger.info("Trimming loaded track")

        cache_key = unwrap(trim_form.cache_key.data)
        file_name = unwrap(trim_form.orig_file_name.data)
        start_idx = int(trim_form.start_idx.data)
        end_idx = int(trim_form.end_idx.data)
        cached_track_data = cache.get(cache_key)
        if cached_track_data is None:
            flash(
                "Time out. Please finish your modifications within %s (HH:MM:SS)"
                % format_timedelta(timedelta(seconds=track_cache_timeout_seconds)),
                "alert-warning",
            )
        else:
            track = ByteTrack(cached_track_data)
            logger.debug("Trimming to %s -> %s", start_idx, end_idx)
            # NOTE: This should be an option toggle or not even a thing once support by
            # geo-track-analyer
            track.strip_segements()
            track.track.segments[0].points = track.track.segments[0].points[
                start_idx:end_idx
            ]

            binary_data = BytesIO(track.get_xml().encode())

            return send_file(
                binary_data,
                download_name=f"{file_name}_trimmed.gpx",
                as_attachment=True,
            )  # type: ignore

    if trim_database_form.validate_on_submit():
        form_track_id = int(unwrap(trim_database_form.track_id.data))
        start_idx = int(trim_database_form.start_idx.data)
        end_idx = int(trim_database_form.end_idx.data)

        logger.info("Trimming track %s", form_track_id)
        db_track = orm_db.get_or_404(DatabaseTrack, form_track_id)
        track = ByteTrack(db_track.content)

        # NOTE: This should be an option toggle or not even a thing once support by
        # geo-track-analyer
        track.strip_segements()
        track.track.segments[0].points = track.track.segments[0].points[
            start_idx:end_idx
        ]

        if update_track_content(form_track_id, track.get_xml().encode()):
            update_track_overview(
                form_track_id,
                initialize_overviews(track, form_track_id),
            )

            ride_id = get_ride_for_track(form_track_id)
            assert ride_id is not None
            cache.clear()
            return redirect(url_for("ride.display", id_ride=ride_id))

        else:
            flash("Updating trakc content failed" "alert-warning")

    return render_template(
        "trim_track.html",
        active_page="utils_shorten",
        form=form,
        track_id=track_id,
        trim_form=trim_form,
        trim_database_form=trim_database_form,
        state=state,
        map_data=map_data,
        n_points=n_points,
    )


@bp.route("add_segments/<int:id_track>", methods=("GET", "POST"))
def add_segments(id_track: int) -> str | Response:
    db_track = orm_db.get_or_404(DatabaseTrack, id_track)
    track = ByteTrack(db_track.content)

    map_data, n_points = _get_map_data(track)
    marker_indices = [0]
    save_enabled = False

    if request.method == "POST":
        submit_type = request.form.get("submit_type")
        assert submit_type in ["preview", "save"]
        marker_indices = unwrap(request.form.get("submit_indices")).split(",")
        save_enabled = True
        if submit_type == "preview":
            logger.debug("Adding segments --- Preview mode")
        else:
            logging.info("Adding segemnts to track %s", id_track)
            ride_id = get_ride_for_track(id_track)
            cache.clear()
            return redirect(url_for("ride.display", id_ride=ride_id))

    return render_template(
        "segment_track.html",
        active_page="placeholder",
        id_track=id_track,
        map_data=map_data,
        n_points=n_points,
        marker_indices="[" + ",".join(map(str, marker_indices)) + "]",
        save_enabled=save_enabled,
    )
