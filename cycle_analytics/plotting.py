import base64
from typing import Literal, Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from flask import current_app
from geo_track_analyzer.track import Track

from cycle_analytics.database.converter import convert_ride_overview_container_to_df
from cycle_analytics.model.base import RideOverviewContainer
from cycle_analytics.utils.debug import log_timing

month_label_order = dict(
    month=[
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "Mai",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    ]
)


@log_timing
def get_track_thumbnails(data: pd.DataFrame) -> go.Figure:
    return simple_coordinate_plot(data, "latitude", "longitude")


@log_timing
def convert_fig_to_base64(figs: list[go.Figure], width: int, height: int) -> list[str]:
    return [
        base64.b64encode(
            fig.to_image(format="png", width=width, height=height)
        ).decode()
        for fig in figs
    ]


@log_timing
def simple_coordinate_plot(
    data: pd.DataFrame, x: str, y: str, color: str = "white"
) -> go.Figure:
    fig = px.line(data[data.moving], x=x, y=y)
    fig["data"][0]["line"]["color"] = color  # type: ignore
    fig["data"][0]["line"]["width"] = 5  # type: ignore

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        margin=dict(l=0, r=0, t=0, b=0),
    )
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)

    return fig


def update_elevation_axis(fig: go.Figure, min_elevation: float = 200) -> None:
    range_min, range_max = fig.layout.yaxis.range
    orig_range_diff = range_max - range_min
    if orig_range_diff < 200:
        fig.update_layout(yaxis=dict(range=[range_min, range_min + 200]))


def per_month_overview_plots(
    rides: list[RideOverviewContainer],
    plot_values: list[tuple[str, str, str, str, bool]],
    width: int = 1000,
    height: int = 600,
    color_sequence: Optional[list[str]] = None,
    dark_mode: bool = True,
) -> list[tuple[str, str]]:
    """
    Takes a dataframe and plots the passed plot_values per month

    :param data: Requires columns month, year and all passed in PLOT_VALUES
    :param plot_values: Setting for individual plots to be generated. List of tuples
                        containing *column to plot*, *aggregation function*, *title*,
                        *y-axis title*, and *flag for enabling cumulative plot*
    :param color_sequence:
    :param width:
    :param height:
    :return: List of base64 encoded pngs for each passed plot_value element
    """

    data = convert_ride_overview_container_to_df(rides)

    plots = []
    years = list(data.year.unique())
    if not years:
        raise RuntimeError

    n_years = len(years)
    if color_sequence and n_years > len(color_sequence):
        raise RuntimeError

    for plot_value, agg, title, ytitle, enable_cum in plot_values:
        fig = go.Figure()

        for i, year in enumerate(data.year.unique()):
            histo_args = {
                "name": str(year),
                "x": data[data.year == year]["month"],
                "y": data[data.year == year][plot_value],
                "histfunc": agg,
                "cumulative_enabled": enable_cum,
            }
            if color_sequence:
                histo_args["marker_color"] = color_sequence[i]
            fig.add_trace(go.Histogram(**histo_args))

        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            bargap=0.2 if not enable_cum else 0,
            title=title,
            xaxis_title="",
            yaxis_title=ytitle,
        )
        fig.update_xaxes(
            categoryorder="array",
            categoryarray=month_label_order["month"],
        )
        if enable_cum:
            fig.update_layout(barmode="stack")

        if dark_mode:
            fig.update_layout(font_color="white")

        plots.append(fig)

    base64_plots = convert_fig_to_base64(plots, width=width, height=height)
    return [(base64_plots[i], plot_values[i][2]) for i in range(len(plot_values))]


def get_track_elevation_plot(
    track: Track,
    include_velocity: bool,
    segment: None | int | list[int] = None,
    pois: Optional[list[tuple[float, float]]] = None,
    color_elevation: Optional[str] = None,
    color_velocity: Optional[str] = None,
    color_poi: Optional[str] = None,
    slider: bool = False,
    show_segment_borders: bool = False,
) -> go.Figure:
    elevation_plot = track.plot(
        kind="profile",
        segment=segment,
        height=None,
        width=None,
        include_velocity=include_velocity,
        pois=pois,
        color_elevation=color_elevation,
        color_additional_trace=color_velocity,
        color_poi=color_poi,
        slider=slider,
        show_segment_borders=show_segment_borders,
        color_segment_border=current_app.config.style.color_border,
    )
    update_elevation_axis(elevation_plot, 200)

    elevation_plot.update_layout(
        autosize=True,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    elevation_plot.update_layout(font_color="white")

    elevation_plot.update_xaxes(showgrid=True, gridwidth=1, gridcolor="Gray")
    elevation_plot.update_yaxes(showgrid=True, gridwidth=1, gridcolor="Gray")

    return elevation_plot


def get_track_elevation_extension_plot(
    track: Track,
    plot_extension: Literal["heartrate", "cadence", "power"],
    segment: None | int | list[int] = None,
    color_elevation: Optional[str] = None,
    color_extention: Optional[str] = None,
    slider: bool = False,
    show_segment_borders: bool = False,
) -> go.Figure:
    elevation_plot = track.plot(
        kind="profile",
        segment=segment,
        height=None,
        width=None,
        color_elevation=color_elevation,
        color_additional_trace=color_extention,
        slider=slider,
        include_heartrate=plot_extension == "heartrate",
        include_cadence=plot_extension == "cadence",
        include_power=plot_extension == "power",
        show_segment_borders=show_segment_borders,
        color_segment_border=current_app.config.style.color_border,
    )

    update_elevation_axis(elevation_plot, 200)

    elevation_plot.update_layout(
        autosize=True,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    elevation_plot.update_layout(font_color="white")

    elevation_plot.update_xaxes(showgrid=True, gridwidth=1, gridcolor="Gray")
    elevation_plot.update_yaxes(showgrid=True, gridwidth=1, gridcolor="Gray")

    return elevation_plot


def get_track_elevation_slope_plot(
    track: Track,
    color_neutral: str,
    color_min: str,
    color_max: str,
    intervals: int = 200,
    slider: bool = False,
    segment: None | int | list[int] = None,
    show_segment_borders: bool = False,
) -> go.Figure:
    fig = track.plot(
        kind="profile-slope",
        segment=segment,
        reduce_pp_intervals=intervals,
        slope_gradient_color=(color_min, color_neutral, color_max),
        height=None,
        width=None,
        slider=slider,
        show_segment_borders=show_segment_borders,
        color_segment_border=current_app.config.style.color_border,
    )

    update_elevation_axis(fig, 200)

    fig.update_layout(
        autosize=True,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    fig.update_layout(font_color="white")

    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor="Gray")
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="Gray")

    return fig
