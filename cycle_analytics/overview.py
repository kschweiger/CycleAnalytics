import json
from datetime import date

import pandas as pd
import plotly
import plotly.express as px
from data_organizer.db.exceptions import QueryReturnedNoData
from flask import Blueprint, current_app, render_template, request, url_for
from gpx_track_analyzer.utils import center_geolocation

from cycle_analytics.forms import YearAndRideTypeForm
from cycle_analytics.plotting import per_month_overview_plots
from cycle_analytics.queries import (
    get_rides_in_timeframe,
    get_track_for_id,
    get_years_in_database,
)
from cycle_analytics.utils import get_nice_timedelta_isoformat

bp = Blueprint("overview", __name__, url_prefix="/overview")


@bp.route("/", methods=("GET", "POST"))
def main():
    config = current_app.config

    overview_form = YearAndRideTypeForm()
    type_choices = ["All"] + config.adders.ride.type_choices

    overview_form.ride_type.choices = [
        ("Default", " , ".join(config.overview.default_types))
    ] + [(c, c) for c in type_choices]

    curr_year = date.today().year
    overview_form.year.choices = (
        [(str(curr_year), str(curr_year))]
        + [(str(y), str(y)) for y in get_years_in_database() if y != curr_year]
        + [("All", "All")]
    )
    selected_year = overview_form.year.data

    table_headings = [
        "Date",
        "Ride Time",
        "Total Time",
        "Distance [km]",
        "Avg. Velocity [km/h]",
        "Uphill [m]",
        "Downhill [m]",
    ]
    table_data = []
    try:
        select_ride_types_ = overview_form.ride_type.data
        if select_ride_types_ == "Default":
            select_ride_types = config.overview.default_types
        else:
            select_ride_types = select_ride_types_

        rides = get_rides_in_timeframe(selected_year, ride_type=select_ride_types)
    except QueryReturnedNoData:
        rides = pd.DataFrame()

    for rcrd in rides.to_dict("records"):
        # thumbnails = get_thumbnails_for_id(rcrd["id_ride"])
        table_data.append(
            (
                (
                    rcrd["date"].isoformat(),
                    url_for("ride.display", id_ride=rcrd["id_ride"]),
                ),
                ""
                if pd.isna(rcrd["ride_time"])
                else get_nice_timedelta_isoformat(rcrd["ride_time"].isoformat()),
                get_nice_timedelta_isoformat(rcrd["total_time"].isoformat()),
                rcrd["distance"],
                ""
                if pd.isna(rcrd["avg_velocity_kmh"])
                else round(rcrd["avg_velocity_kmh"], 2),
                ""
                if pd.isna(rcrd["uphill_elevation"])
                else round(rcrd["uphill_elevation"], 2),
                ""
                if pd.isna(rcrd["downhill_elevation"])
                else round(rcrd["downhill_elevation"], 2),
            )
        )

    plots_ = []
    if not rides.empty:
        plots_ = per_month_overview_plots(
            rides,
            [
                ("id_ride", "count", "Number of rides per Month", "Count", False),
                ("distance", "sum", "Distance per Month", "Distance [km]", False),
                (
                    "distance",
                    "avg",
                    "Average ride distance per Month",
                    "Distance [km]",
                    False,
                ),
                (
                    "distance",
                    "sum",
                    "Cumulative distance per Month",
                    "Distance [km]",
                    True,
                ),
            ],
            width=1200,
            color_sequence=current_app.config.style.color_sequence,
        )

    plots = []
    for i in range(0, len(plots_), 2):
        plots.append(plots_[i : i + 2])

    return render_template(
        "overview.html",
        active_page="overview",
        overview_form=overview_form,
        year_selected=str(selected_year),
        # years=years,
        table_data=(table_headings, table_data),
        plots=plots,
    )


@bp.route("/heatmap", methods=("GET", "POST"))
def heatmap():
    heatmap_plot = None
    year_selected = request.args.get("year_selected")

    rides = get_rides_in_timeframe(year_selected)

    rides_w_track = rides[rides.id_track.notna()].id_ride.to_list()
    # TODO: Do this multithreaded?
    datas = []
    for ride_id in rides_w_track:
        data = get_track_for_id(ride_id).get_segment_data()
        datas.append(data[data.moving])

    data = pd.concat(datas)

    center_lat, center_lon = center_geolocation(
        [(r["latitude"], r["longitude"]) for r in data.to_dict("records")]
    )

    fig = px.density_mapbox(
        data,
        lat="latitude",
        lon="longitude",
        radius=5,
        center=dict(lat=center_lat, lon=center_lon),
        zoom=11,
        mapbox_style="carto-positron",
        color_continuous_scale=px.colors.sequential.Viridis,
        range_color=[0, len(datas) / 2],
        height=800,
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    fig.update_layout(font_color="white")

    heatmap_plot = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

    return render_template(
        "visualizations/heatmap.html",
        active_page="overview",
        year_selected=year_selected,
        heatmap_plot=heatmap_plot,
    )
