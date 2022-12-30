import json
from datetime import datetime

import plotly
from data_organizer.db.exceptions import QueryReturnedNoData
from flask import Blueprint, current_app, flash, redirect, render_template, url_for
from gpx_track_analyzer.visualize import plot_track_2d

from cycle_analytics.model import MapData, MapPathData
from cycle_analytics.queries import get_full_ride_data, get_track_for_id

bp = Blueprint("ride", __name__, url_prefix="/ride")


@bp.route("/<int:id_ride>/", methods=("GET", "POST"))
def display(id_ride: int):
    try:
        data = get_full_ride_data(id_ride)
    except QueryReturnedNoData:
        flash("Invalid value of id_ride. Redirecting to overview", "alert-danger")
        return redirect(url_for("overview.main"))
    print(data)

    ride_date = data["date"]
    ride_from = data["start_time"]
    ride_to = (
        datetime.combine(ride_date, data["start_time"]) + data["total_time"]
    ).time()

    ride_data = [
        ("Duration", data["total_time"]),
        ("Duration (ridden)", data["ride_time"]),
        ("Distance [km]", data["distance"]),
        ("Bike", data["bike"]),
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
        plot2d = plot_track_2d(
            track_segment_data,
            height=None,
            width=None,
            include_velocity=True,
        )

        plot2d.update_layout(
            autosize=True,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        plot2d.update_layout(font_color="white")

        plot2d.update_xaxes(showgrid=True, gridwidth=1, gridcolor="Gray")
        plot2d.update_yaxes(showgrid=True, gridwidth=1, gridcolor="Gray")

        # TEMP: Add color option ot track analyzer
        colors = current_app.config.style.color_sequence
        plot2d.data[0].marker.color = colors[0]
        plot2d.data[1].marker.color = colors[1]

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
    )
