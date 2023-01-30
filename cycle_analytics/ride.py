import json
from datetime import datetime

import plotly
from data_organizer.db.exceptions import QueryReturnedNoData
from flask import Blueprint, current_app, flash, redirect, render_template, url_for

from cycle_analytics.model import MapData, MapMarker, MapPathData
from cycle_analytics.plotting import get_track_elevation_plot
from cycle_analytics.queries import (
    get_events_for_ride,
    get_full_ride_data,
    get_track_for_id,
)

bp = Blueprint("ride", __name__, url_prefix="/ride")


@bp.route("/<int:id_ride>/", methods=("GET", "POST"))
def display(id_ride: int):
    config = current_app.config
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

    if data["id_track"] is not None:
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
    )
