import base64
from typing import Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

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
    years = data.year.unique()
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

        if dark_mode:
            fig.update_layout(font_color="white")

        plots.append(fig)

    base64_plots = convert_fig_to_base64(plots, width=width, height=height)
    ret_plots = [(base64_plots[i], plot_values[i][2]) for i in range(len(plot_values))]
    return ret_plots
