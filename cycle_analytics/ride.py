import json
import logging
from datetime import datetime

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
from track_analyzer import ByteTrack
from track_analyzer.exceptions import VisualizationSetupError
from werkzeug import Response
from wtforms import (
    StringField,
)
from wtforms.validators import DataRequired

from cycle_analytics.database.model import Ride
from cycle_analytics.database.model import db as orm_db
from cycle_analytics.db import get_db
from cycle_analytics.model.base import MapData, MapMarker, MapPathData
from cycle_analytics.plotting import (
    get_track_elevation_extension_plot,
    get_track_elevation_plot,
    get_track_elevation_slope_plot,
)
from cycle_analytics.queries import (
    get_note,
    modify_note,
)
from cycle_analytics.utils.base import none_or_round
from cycle_analytics.utils.forms import get_track_data_from_form
from cycle_analytics.utils.track import add_track_to_db

bp = Blueprint("ride", __name__, url_prefix="/ride")

logger = logging.getLogger(__name__)


class AddTrackForm(FlaskForm):
    track = FileField("GPX Track")
    replace = StringField("Replace", default="0", validators=[DataRequired()])


@bp.route("/<int:id_ride>/", methods=("GET", "POST"))
def display(id_ride: int) -> str | Response:
    config = current_app.config

    form = AddTrackForm()

    ride = orm_db.get_or_404(Ride, id_ride)

    show_track_add_from = True
    if form.validate_on_submit():
        add_track_to_db(
            data=get_track_data_from_form(form, "track"),
            replace=form.replace.data == "1",
            id_ride=id_ride,
        )

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
        ride_data.append(("Note", note))
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
    try:
        track_overview = ride.track_overview
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

    if track and database_track:
        show_track_add_from = False
        if not has_enhanced_track:
            logger.debug("Found raw track data but no enhanced track data")
            show_track_enhance_from = True
        id_track = database_track.id
        track_segment_data = track.get_segment_data(0)

        colors = current_app.config.style.color_sequence

        plot2d = get_track_elevation_plot(
            track_segment_data,
            True,
            color_elevation=colors[0],
            color_velocity=colors[1],
            slider=True,
        )

        plot_elevation_and_velocity = json.dumps(
            plot2d, cls=plotly.utils.PlotlyJSONEncoder
        )

        lats = track_segment_data[track_segment_data.moving].latitude.to_list()
        lats = ",".join([str(l) for l in lats])  # noqa: E741
        longs = track_segment_data[track_segment_data.moving].longitude.to_list()
        longs = ",".join([str(l) for l in longs])  # noqa: E741

        map_data = MapData(path=MapPathData(latitudes=lats, longitudes=longs))

        slope_colors = current_app.config.style.slope_colors
        slope_figure = get_track_elevation_slope_plot(
            track,
            0,
            slope_colors.neutral,
            slope_colors.min,
            slope_colors.max,
            slider=True,
        )
        slope_plot = json.dumps(slope_figure, cls=plotly.utils.PlotlyJSONEncoder)

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        try:
            hr_figure = get_track_elevation_extension_plot(
                track_segment_data,
                "heartrate",
                color_elevation=colors[0],
                color_extention=colors[1],
                slider=True,
            )
        except VisualizationSetupError:
            hr_plot = None
        else:
            hr_plot = json.dumps(hr_figure, cls=plotly.utils.PlotlyJSONEncoder)
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        try:
            cad_figure = get_track_elevation_extension_plot(
                track_segment_data,
                "cadence",
                color_elevation=colors[0],
                color_extention=colors[1],
                slider=True,
            )
        except VisualizationSetupError:
            cad_plot = None
        else:
            cad_plot = json.dumps(cad_figure, cls=plotly.utils.PlotlyJSONEncoder)

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        try:
            pw_figure = get_track_elevation_extension_plot(
                track_segment_data,
                "power",
                color_elevation=colors[0],
                color_extention=colors[1],
                slider=True,
            )
        except VisualizationSetupError:
            pw_plot = None
        else:
            pw_figure.show()
            pw_plot = json.dumps(pw_figure, cls=plotly.utils.PlotlyJSONEncoder)

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
        plot_elevation_and_velocity=plot_elevation_and_velocity,
        slope_plot=slope_plot,
        heartrate_plot=hr_plot,
        cadence_plot=cad_plot,
        power_plot=pw_plot,
        map_data=map_data,
        located_events=located_events,
        form=form,
        show_track_add_from=show_track_add_from,
        show_track_enhance_from=show_track_enhance_from,
        id_raw_track=-999,  # FIXME
        has_note=has_note,
    )


@bp.route("add_note/<int:id_ride>/", methods=("GET", "POST"))
def add_note(id_ride: int) -> str | Response:
    current_note_value = get_note(id_ride)

    if request.method == "POST":
        print(request.form.get("note"))
        new_note_value = request.form.get("note")
        db = get_db()
        if current_note_value is None:
            insert_succ, err = db.insert(
                current_app.config.tables_as_settings["ride_notes"],
                [[id_ride, new_note_value]],
            )
            succ_msg = "Note added"
        else:
            insert_succ = modify_note(id_ride, new_note_value)
            err = "Error on update. See log"
            succ_msg = "Note updated"
        if insert_succ:
            flash(succ_msg, "alert-success")
            return redirect(url_for("ride.display", id_ride=id_ride))
        else:
            flash(f"Note could not be inserted: {err}", "alert-danger")

    return render_template(
        "adders/ride_note.html",
        active_page="overview",
        id_ride=id_ride,
        prefill_note_value=current_note_value,
    )
