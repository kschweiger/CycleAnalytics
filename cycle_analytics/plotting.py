import base64
from typing import Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from gpx_track_analyzer.track import Track
from gpx_track_analyzer.visualize import plot_track_2d, plot_track_with_slope

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


def get_track_thumbnails(data: pd.DataFrame) -> list[go.Figure]:
    coordinate_plot = simple_coordinate_plot(data, "latitude", "longitude")

    return [coordinate_plot]


def convert_fig_to_base64(figs: list[go.Figure], width: int, height: int) -> list[str]:
    return [
        base64.b64encode(
            fig.to_image(format="png", width=width, height=height)
        ).decode()
        for fig in figs
    ]


def simple_coordinate_plot(
    data: pd.DataFrame, x: str, y: str, color: str = "white"
) -> go.Figure:
    fig = px.line(data[data.moving], x=x, y=y)
    fig["data"][0]["line"]["color"] = color
    fig["data"][0]["line"]["width"] = 5

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        margin=dict(l=0, r=0, t=0, b=0),
    )
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)

    return fig


def per_month_overview_plots(
    data: pd.DataFrame,
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
    ret_plots = [(base64_plots[i], plot_values[i][2]) for i in range(len(plot_values))]
    return ret_plots


def get_track_elevation_plot(
    segment_data: pd.DataFrame,
    include_velocity: bool,
    pois: Optional[list[tuple[float, float]]] = None,
    color_elevation: Optional[str] = None,
    color_velocity: Optional[str] = None,
    color_poi: Optional[str] = None,
    slider: bool = False,
) -> go.Figure:
    elevation_plot = plot_track_2d(
        segment_data,
        height=None,
        width=None,
        include_velocity=include_velocity,
        pois=pois,
        color_elevation=color_elevation,
        color_velocity=color_velocity,
        color_poi=color_poi,
        slider=slider,
    )

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
    n_segment: int,
    color_neutral: str,
    color_min: str,
    color_max: str,
    intervals: float = 200,
    slider: bool = False,
) -> go.Figure:
    fig = plot_track_with_slope(
        track,
        n_segment,
        intervals,
        (color_min, color_neutral, color_max),
        height=None,
        width=None,
        slider=slider,
    )

    fig.update_layout(
        autosize=True,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    fig.update_layout(font_color="white")

    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor="Gray")
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="Gray")

    return fig
