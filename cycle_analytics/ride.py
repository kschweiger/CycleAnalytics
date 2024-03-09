import json
import logging
from collections import deque
from datetime import datetime, timedelta

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
from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from geo_track_analyzer import ByteTrack
from geo_track_analyzer.exceptions import VisualizationSetupError
from sqlalchemy import select
from werkzeug import Response
from wtforms import (
    RadioField,
    StringField,
)
from wtforms.validators import DataRequired

from cycle_analytics.database.model import (
    DatabaseLocation,
    Ride,
    RideNote,
    TrackLocationAssociation,
)
from cycle_analytics.database.model import db as orm_db
from cycle_analytics.database.modifier import switch_overview_of_interest_flag
from cycle_analytics.model.base import MapData, MapMarker, MapPathData
from cycle_analytics.plotting import (
    get_track_elevation_extension_plot,
    get_track_elevation_plot,
    get_track_elevation_slope_plot,
)
from cycle_analytics.track import _match_locations
from cycle_analytics.utils.base import (
    convert_locations_to_markers,
    format_timedelta,
    none_or_round,
    unwrap,
)
from cycle_analytics.utils.forms import get_track_from_form
from cycle_analytics.utils.track import init_db_track_and_enhance

bp = Blueprint("ride", __name__, url_prefix="/ride")

logger = logging.getLogger(__name__)


class AddTrackForm(FlaskForm):
    track = FileField("GPX Track")
    enhance_elevation = RadioField(
        "Enhance Elevation",
        choices=[(True, "Enhance Elevation")],
        coerce=bool,
        validate_choice=False,
    )
    replace = StringField("Replace", default="0", validators=[DataRequired()])


@bp.route("/<int:id_ride>/", methods=("GET", "POST"))
def display(id_ride: int) -> str | Response:
    config = current_app.config

    form = AddTrackForm()
    form.enhance_elevation.data = True

    ride = orm_db.get_or_404(Ride, id_ride)

    raw_form_processed = False
    show_all_segments_clicked = False
    modify_segments_clicked = False
    visualize_segments = False
    if request.method == "POST":
        # Deal with the show all segment form
        if request.form.get("segment_control_form") is not None:
            raw_form_processed = True
            if request.form.get("show_all_btn") is not None:
                show_all_segments_clicked = True
            if request.form.get("mod_interest_btn") is not None:
                modify_segments_clicked = True
            if request.form.get("visualize_segments") is not None:
                visualize_segments = True

        # Deal with the hide/unhide form
        if request.form.get("updated_hidden_state") is not None:
            raw_form_processed = True
            for idx in [
                int(k.replace("current_value_segment_hide_", ""))
                for k in request.form.keys()
                if k.startswith("current_value_segment_hide_")
            ]:
                # Was false is switched to "of interest"
                if (
                    unwrap(request.form.get(f"current_value_segment_hide_{idx}")) == "0"
                    and request.form.get(f"segment_hide_checkbox_{idx}") is not None
                ):
                    logger.debug("Switching value of overview %s to of interest", idx)
                    switch_overview_of_interest_flag(idx)
                # Was true is switched to not "of interest"
                elif (
                    unwrap(request.form.get(f"current_value_segment_hide_{idx}")) == "1"
                    and request.form.get(f"segment_hide_checkbox_{idx}") is None
                ):
                    logger.debug(
                        "Switching value of overview %s to NOT of interest", idx
                    )
                    switch_overview_of_interest_flag(idx)

    show_track_add_from = True
    if form.validate_on_submit() and not raw_form_processed:
        try:
            track = get_track_from_form(form, "track")
        except RuntimeError as e:
            flash("Error: %s" % e, "alert-danger")
        else:
            tracks_to_insert = init_db_track_and_enhance(
                track=track, is_enhanced=not bool(form.enhance_elevation.data)
            )
            for track in tracks_to_insert:
                _match_locations(track)
            if form.replace.data == "1":
                for tr_ in ride.tracks:
                    orm_db.session.delete(tr_)
                    # orm_db.session.commit()
            ride.tracks = tracks_to_insert
            orm_db.session.commit()

    show_track_enhance_from = False

    ride_date = ride.ride_date
    ride_from = ride.start_time
    ride_to = (
        datetime.combine(ride_date, ride.start_time) + ride.total_duration
    ).time()

    ride_data = [
        ("Duration", ride.total_duration),
        ("Duration (ridden)", ride.ride_duration),
        ("Distance [km]", ride.distance),
        ("Bike", (ride.bike.name, url_for("bike.show", bike_name=ride.bike.name))),
        ("Type", ride.terrain_type),
    ]
    has_note = False
    for note in ride.notes:
        ride_data.append(("Note", note.text))
        has_note = True

    if ride.tracks:
        logger.debug("Disabling form because ride has raw track")
        show_track_add_from = False

    has_enhanced_track = any([t.is_enhanced for t in ride.tracks])

    database_track = ride.database_track
    track = None
    if database_track:
        track = ByteTrack(database_track.content)

    track_data = None
    track_overview = None
    segment_overviews = None
    try:
        track_overview, segment_overviews = ride.track_overviews
    except RuntimeError:
        pass

    if track_overview:
        track_data = [
            (
                "Distance (moving) [km]",
                round(track_overview.moving_distance / 1000, 2),
            ),
            ("Max velocity [km/h]", round(track_overview.max_velocity_kmh, 2)),
            ("Avg velocity [km/h]", round(track_overview.avg_velocity_kmh, 2)),
            ("Max elevation [m]", none_or_round(track_overview.max_elevation, 2)),
            ("Min elevation [m]", none_or_round(track_overview.min_elevation, 2)),
            ("Uphill [m]", none_or_round(track_overview.uphill_elevation, 2)),
            ("Downhill [m]", none_or_round(track_overview.downhill_elevation, 2)),
        ]
    colors = current_app.config.style.color_sequence

    segment_table = None
    plot_segments = None
    segment_colors = None
    if segment_overviews and len(segment_overviews) > 1:
        segment_table_header = [
            "#",
            "Distance [km]",
            "Max velocity [km/h]",
            "Avg velocity [km/h]",
            "Duration",
        ]
        segment_table_data = []
        plot_segments = []
        segment_colors = []
        color_deque = deque(colors)
        for idx_segment, segment_overview in enumerate(segment_overviews):
            if not show_all_segments_clicked and not segment_overview.of_interest:
                continue
            segment_table_data.append(
                [
                    idx_segment,
                    round(segment_overview.moving_distance / 1000, 2),
                    round(segment_overview.max_velocity_kmh, 2),
                    round(segment_overview.avg_velocity_kmh, 2),
                    format_timedelta(
                        timedelta(seconds=segment_overview.moving_time_seconds)
                    ),
                    (segment_overview.id, segment_overview.of_interest),
                ]
            )
            plot_segments.append(idx_segment)
            segment_colors.append(color_deque[0])
            color_deque.rotate(-1)
        segment_table = (
            segment_table_header,
            segment_table_data,
            segment_colors,
        )

    location_markers = []
    if track and database_track:
        show_track_add_from = False
        if not has_enhanced_track:
            logger.debug("Found raw track data but no enhanced track data")
            show_track_enhance_from = True
        id_track = database_track.id
        track_segment_data = track.get_track_data()
        if visualize_segments and plot_segments is not None:
            n_pre = len(track_segment_data)
            track_segment_data = track_segment_data[
                track_segment_data.segment.isin(plot_segments)
            ]
            logger.debug(
                "Selection segments %s -> Dropped %s points",
                plot_segments,
                n_pre - len(track_segment_data),
            )
            paths = []
            color_deque = deque(colors)
            for plot_idx_segment in plot_segments:
                lats = track_segment_data[
                    (track_segment_data.moving)
                    & (track_segment_data.segment == plot_idx_segment)
                ].latitude.to_list()
                lats = ",".join([str(l) for l in lats])  # noqa: E741
                longs = track_segment_data[
                    (track_segment_data.moving)
                    & (track_segment_data.segment == plot_idx_segment)
                ].longitude.to_list()
                longs = ",".join([str(l) for l in longs])  # noqa: E741
                paths.append(
                    MapPathData(latitudes=lats, longitudes=longs, color=color_deque[0])
                )
                color_deque.rotate(-1)
        else:
            lats = track_segment_data[track_segment_data.moving].latitude.to_list()
            lats = ",".join([str(l) for l in lats])  # noqa: E741
            longs = track_segment_data[track_segment_data.moving].longitude.to_list()
            longs = ",".join([str(l) for l in longs])  # noqa: E741
            paths = [MapPathData(latitudes=lats, longitudes=longs)]

        map_data = MapData(paths=paths)

        plot2d = get_track_elevation_plot(
            track,
            not track_segment_data.speed.isna().all(),
            segment=None if not visualize_segments else plot_segments,
            color_elevation=colors[0],
            color_velocity=colors[1],
            slider=True,
            show_segment_borders=visualize_segments and plot_segments is not None,
        )

        plot_elevation_and_velocity = json.dumps(
            plot2d, cls=plotly.utils.PlotlyJSONEncoder
        )

        slope_colors = current_app.config.style.slope_colors
        slope_figure = get_track_elevation_slope_plot(
            track=track,
            color_neutral=slope_colors.neutral,
            color_min=slope_colors.min,
            color_max=slope_colors.max,
            slider=True,
            segment=None if not visualize_segments else plot_segments,
            show_segment_borders=visualize_segments and plot_segments is not None,
        )
        slope_plot = json.dumps(slope_figure, cls=plotly.utils.PlotlyJSONEncoder)

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        try:
            hr_figure = get_track_elevation_extension_plot(
                track,
                "heartrate",
                segment=None if not visualize_segments else plot_segments,
                color_elevation=colors[0],
                color_extention=colors[1],
                slider=True,
                show_segment_borders=visualize_segments and plot_segments is not None,
            )
        except VisualizationSetupError:
            hr_plot = None
        else:
            hr_plot = json.dumps(hr_figure, cls=plotly.utils.PlotlyJSONEncoder)
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        try:
            cad_figure = get_track_elevation_extension_plot(
                track,
                "cadence",
                segment=None if not visualize_segments else plot_segments,
                color_elevation=colors[0],
                color_extention=colors[1],
                slider=True,
                show_segment_borders=visualize_segments and plot_segments is not None,
            )
        except VisualizationSetupError:
            cad_plot = None
        else:
            cad_plot = json.dumps(cad_figure, cls=plotly.utils.PlotlyJSONEncoder)

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        try:
            pw_figure = get_track_elevation_extension_plot(
                track,
                "power",
                segment=None if not visualize_segments else plot_segments,
                color_elevation=colors[0],
                color_extention=colors[1],
                slider=True,
                show_segment_borders=visualize_segments and plot_segments is not None,
            )
        except VisualizationSetupError:
            pw_plot = None
        else:
            pw_plot = json.dumps(pw_figure, cls=plotly.utils.PlotlyJSONEncoder)

        assoications = orm_db.session.execute(
            select(TrackLocationAssociation).filter(
                TrackLocationAssociation.track_id == database_track.id
            )
        ).scalars()

        database_locations = []
        for assoication in assoications:
            database_locations.append(
                orm_db.get_or_404(DatabaseLocation, assoication.location_id)
            )
        location_markers = convert_locations_to_markers(database_locations)

    else:
        id_track = None  # type: ignore
        plot_elevation_and_velocity = None
        map_data = None
        slope_plot = None
        hr_plot = None
        cad_plot = None
        pw_plot = None

    located_events = []
    if ride.events:
        event_colors = config.mappings.event_colors.to_dict()
        for event in ride.events:
            if event.latitude is not None and event.longitude is not None:
                color = "blue"
                if event.event_type.text in event_colors.keys():
                    color = event_colors[event.event_type.text]

                popup_text = f"<b>{event.short_description}</b>"
                if event.severity is not None:
                    popup_text += f" - Severity: {event.severity!s}"
                if event.description is not None:
                    popup_text += f"<br>{event.description}"
                located_events.append(
                    MapMarker(
                        latitude=event.latitude,
                        longitude=event.longitude,
                        popup_text=popup_text,
                        color=color,
                        color_idx=0
                        if event.severity is None
                        else event.severity.id - 1,
                    )
                )

    return render_template(
        "ride.html",
        active_page="overview",
        id_ride=id_ride,
        ride_date=ride_date,
        ride_from=ride_from,
        ride_to=ride_to,
        ride_data=ride_data,
        id_track=id_track,
        track_data=track_data,
        segment_table=segment_table,
        show_all_segments_clicked=show_all_segments_clicked,
        modify_segments_clicked=modify_segments_clicked,
        visualize_segments_clicked=visualize_segments,
        plot_elevation_and_velocity=plot_elevation_and_velocity,
        slope_plot=slope_plot,
        heartrate_plot=hr_plot,
        cadence_plot=cad_plot,
        power_plot=pw_plot,
        map_data=map_data,
        map_markers=located_events + location_markers,
        form=form,
        show_track_add_from=show_track_add_from,
        show_track_enhance_from=show_track_enhance_from,
        has_note=has_note,
    )


# TODO: Support multiple notes
@bp.route("add_note/<int:id_ride>", methods=("GET", "POST"))
def add_note(id_ride: int) -> str | Response:
    ride = orm_db.get_or_404(Ride, id_ride)
    current_note_value = None
    if ride.notes:
        current_note_value = ride.notes[0].text

    if request.method == "POST":
        new_note_value = request.form.get("note")
        if ride.notes:
            ride.notes[0].text = new_note_value
            orm_db.session.commit()
            flash("Note updated", "alert-success")
        else:
            ride.notes.append(RideNote(text=unwrap(new_note_value)))
            orm_db.session.commit()
            flash("Note added", "alert-success")
        return redirect(url_for("ride.display", id_ride=id_ride))

    return render_template(
        "adders/ride_note.html",
        active_page="overview",
        id_ride=id_ride,
        prefill_note_value=current_note_value,
    )
