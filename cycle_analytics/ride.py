import json
import logging
from datetime import datetime

import plotly
from data_organizer.db.exceptions import QueryReturnedNoData
from flask import Blueprint, current_app, flash, redirect, render_template, url_for
from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from gpx_track_analyzer.track import ByteTrack

from cycle_analytics.adders import enhance_track
from cycle_analytics.cache import cache
from cycle_analytics.db import get_db
from cycle_analytics.model import MapData, MapMarker, MapPathData
from cycle_analytics.plotting import get_track_elevation_plot
from cycle_analytics.queries import (
    get_events_for_ride,
    get_full_ride_data,
    get_last_track_id,
    get_track_for_id,
    ride_has_track,
)

bp = Blueprint("ride", __name__, url_prefix="/ride")

logger = logging.getLogger(__name__)


class AddTrackForm(FlaskForm):
    track = FileField("GPX Track")


@bp.route("/<int:id_ride>/", methods=("GET", "POST"))
def display(id_ride: int):
    config = current_app.config

    form = AddTrackForm()
    if form.validate_on_submit():
        db = get_db()
        gpx_value = form.track.data.stream.read()
        insert_succ_track, err = db.insert(
            current_app.config.tables_as_settings[
                current_app.config.defaults.raw_track_table
            ],
            [[id_ride, gpx_value]],
        )
        if insert_succ_track:
            flash("Track added", "alert-success")

            track = ByteTrack(gpx_value)
            enhanced_track_data, track_overview_data = enhance_track(track)
            if enhanced_track_data is not None:
                enhance_insert_succ_track, err = db.insert(
                    current_app.config.tables_as_settings[
                        current_app.config.defaults.track_table
                    ],
                    [[id_ride, enhanced_track_data]],
                )
                if enhance_insert_succ_track:
                    flash("Enhanced Track added", "alert-success")
                    if track_overview_data:
                        id_track = get_last_track_id(
                            current_app.config.defaults.track_table, "id_track", True
                        )
                        # Add the id_track to the data for insertion in the db
                        track_overview_data = [
                            [id_track] + seg_data for seg_data in track_overview_data
                        ]
                        overview_insert_succ_track, err = db.insert(
                            current_app.config.tables_as_settings[
                                current_app.config.defaults.track_overview_table
                            ],
                            track_overview_data,
                        )
                        if overview_insert_succ_track:
                            flash(
                                f"Overview inserted for track {id_track}",
                                "alert-success",
                            )
                        else:
                            flash(
                                f"Overview could not be generated: {err[0:250]}",
                                "alert-danger",
                            )
                else:
                    flash(
                        f"Enhanced Track could not be inserted: {err[0:250]}",
                        "alert-danger",
                    )
            logger.warning("Resetting cache")
            cache.clear()
        else:
            flash(f"Track could not be added: {err[0:250]}", "alert-danger")

    try:
        data = get_full_ride_data(id_ride)
    except QueryReturnedNoData:
        flash("Invalid value of id_ride. Redirecting to overview", "alert-danger")
        return redirect(url_for("overview.main"))

    ride_date = data["date"]
    ride_from = data["start_time"]
    ride_to = (
        datetime.combine(ride_date, data["start_time"]) + data["total_time"]
    ).time()

    ride_data = [
        ("Duration", data["total_time"]),
        ("Duration (ridden)", data["ride_time"]),
        ("Distance [km]", data["distance"]),
        ("Bike", (data["bike"], url_for("bike.show", bike_name=data["bike"]))),
        ("Type", data["ride_type"]),
    ]

    if ride_has_track(
        id_ride,
        current_app.config.tables_as_settings[
            current_app.config.defaults.raw_track_table
        ].name,
    ):
        logger.debug("Disabling form because ride has raw track")
        form = None  # type: ignore

    if data["id_track"] is not None:
        form = None  # type: ignore
        track_data = [
            ("Distance (moving) [km]", round(data["moving_distance"] / 1000, 2)),
            ("Max velocity [km/h]", round(data["max_velocity_kmh"], 2)),
            ("Avg velocity [km/h]", round(data["avg_velocity_kmh"], 2)),
            ("Max elevation [m]", round(data["max_elevation"], 2)),
            ("Min elevation [m]", round(data["min_elevation"], 2)),
            ("Uphill [m]", round(data["uphill_elevation"], 2)),
            ("Downhill [m]", round(data["downhill_elevation"], 2)),
        ]
        track = get_track_for_id(id_ride)
        track_segment_data = track.get_segment_data(0)

        colors = current_app.config.style.color_sequence

        plot2d = get_track_elevation_plot(
            track_segment_data,
            True,
            color_elevation=colors[0],
            color_velocity=colors[1],
        )

        plot_elevation_and_velocity = json.dumps(
            plot2d, cls=plotly.utils.PlotlyJSONEncoder
        )

        lats = track_segment_data[track_segment_data.moving].latitude.to_list()
        lats = ",".join([str(l) for l in lats])  # noqa: E741
        longs = track_segment_data[track_segment_data.moving].longitude.to_list()
        longs = ",".join([str(l) for l in longs])  # noqa: E741

        map_data = MapData(path=MapPathData(latitudes=lats, longitudes=longs))

    else:
        track_data = None
        plot_elevation_and_velocity = None
        map_data = None
    events_ = get_events_for_ride(id_ride)
    located_events = []
    if events_:
        severity_mapping = config.mappings.severity.to_dict()
        event_colors = config.mappings.event_colors.to_dict()
        event_dataclass = config.tables_as_settings["events"].dataclass
        events = [event_dataclass(**event_data) for event_data in events_]
        for event in events:
            if event.latitude is not None and event.longitude is not None:
                color = "blue"
                if event.event_type in event_colors.keys():
                    color = event_colors[event.event_type]

                popup_text = f"<b>{event.short_description}</b>"
                if event.severity is not None:
                    popup_text += (
                        f" - Severity: {severity_mapping[str(event.severity)]}"
                    )
                if event.description is not None:
                    popup_text += f"<br>{event.description}"
                located_events.append(
                    MapMarker(
                        latitude=event.latitude,
                        longitude=event.longitude,
                        popup_text=popup_text,
                        color=color,
                        color_idx=0 if event.severity is None else event.severity,
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
        track_data=track_data,
        plot_elevation_and_velocity=plot_elevation_and_velocity,
        map_data=map_data,
        located_events=located_events,
        form=form,
    )
