import concurrent.futures
import json
import logging
from copy import copy
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Dict

import numpy as np
import pandas as pd
import plotly
import plotly.express as px
from flask import Blueprint, Flask, current_app, render_template, request, url_for
from flask_wtf import FlaskForm
from geo_track_analyzer.utils.base import center_geolocation
from wtforms import SelectField
from wtforms.validators import DataRequired

from .database.converter import (
    convert_ride_overview_container_to_df,
)
from .database.model import Ride
from .database.retriever import (
    get_ride_and_latest_track_overview,
    get_ride_years_in_database,
    get_rides_in_timeframe,
)
from .forms import YearAndRideTypeForm
from .plotting import per_month_overview_plots
from .utils import get_month_mapping, get_nice_timedelta_isoformat
from .utils.base import format_timedelta, unwrap

logger = logging.getLogger(__name__)

bp = Blueprint("overview", __name__, url_prefix="/overview")


@dataclass
class JournalCategory:
    name: str
    btn_class: str


@dataclass
class JournalRide:
    id_ride: int
    duration: str
    distance: str
    uphill: None | str
    downhill: None | str
    avg_velocity: None | str
    btn_class: str


@dataclass
class JournalDay:
    date: date
    name: str
    in_month: bool
    highlight_day: bool
    rides: list[JournalRide] = field(default_factory=list)


@dataclass
class JournalWeekSummary:
    duration: str
    distance: str
    uphill: None | str
    downhill: None | str


@dataclass
class JournalWeek:
    week: int
    days: tuple[
        JournalDay,
        JournalDay,
        JournalDay,
        JournalDay,
        JournalDay,
        JournalDay,
        JournalDay,
    ]
    summary: None | JournalWeekSummary = None

    def get_date_range(self) -> tuple[date, date]:
        return next(iter(self.days)).date, list(self.days)[-1].date


weekday_map = {
    1: "Monday",
    2: "Tuesday",
    3: "Wednesday",
    4: "Thursday",
    5: "Friday",
    6: "Saturday",
    7: "Sunday",
}


category_btn_classes = [
    "btn-danger",
    "btn-warning",
    "btn-primary",
    "btn-info",
    "btn-light",
    "btn-dark",
]


class JournalForm(FlaskForm):
    year = SelectField(
        "Year", validators=[DataRequired()], default=str(date.today().year), coerce=int
    )
    month = SelectField(
        "Month",
        validators=[DataRequired()],
        choices=[(i, get_month_mapping()[i]) for i in range(1, 13)],
        default=date.today().month,
        coerce=int,
    )

    ride_type = SelectField("Ride Type", validators=[DataRequired()], default="Default")


@bp.route("/", methods=("GET", "POST"))
def main() -> str:
    config = current_app.config

    overview_form = YearAndRideTypeForm()
    type_choices = ["All"] + config.adders.ride.type_choices

    overview_form.ride_type.choices = [
        ("Default", " , ".join(config.overview.default_types))
    ] + [(c, c) for c in type_choices]

    curr_year = date.today().year

    years = [curr_year] + get_ride_years_in_database()
    year_choices = map(str, ["All"] + sorted(set(years), reverse=True))
    overview_form.year.choices = [(y, y) for y in year_choices]

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
    select_ride_types_ = overview_form.ride_type.data
    if select_ride_types_ == "Default":
        select_ride_types = config.overview.default_types
    else:
        select_ride_types = select_ride_types_

    overview_data = get_ride_and_latest_track_overview(
        selected_year, ride_type=select_ride_types
    )

    for ride_data in overview_data:
        this_ride_data = [
            (
                ride_data.ride_date.date().isoformat(),
                url_for("ride.display", id_ride=ride_data.id_ride),
            ),
            ""
            if ride_data.ride_duration is None
            else format_timedelta(ride_data.ride_duration),
            format_timedelta(ride_data.total_duration),
            ride_data.distance_raw,
        ]
        if ride_data.overview_distance is None:
            this_ride_data.extend(["", "", ""])
        else:
            this_ride_data.extend(
                [
                    ""
                    if ride_data.overview_avg_vel is None
                    else round(ride_data.overview_avg_vel, 2),
                    ""
                    if ride_data.overview_uphill is None
                    else round(ride_data.overview_uphill, 2),
                    ""
                    if ride_data.overview_downhill is None
                    else round(ride_data.overview_downhill, 2),
                ]
            )
        # thumbnails = get_thumbnails_for_id(rcrd["id_ride"])
        table_data.append(tuple(this_ride_data))

    plots_ = []
    if overview_data:
        plots_ = per_month_overview_plots(
            overview_data,
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
                # TODO: Add metrics for ride_time
            ],
            width=1200,
            color_sequence=current_app.config.style.color_sequence,
        )

    plots = [plots_[i : i + 2] for i in range(0, len(plots_), 2)]

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
def heatmap() -> str:
    heatmap_plot = None
    year_selected = int(request.args.get("year_selected", date.today().year))

    rides = get_rides_in_timeframe(year_selected)

    datas = []

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=current_app.config.threadpool  # type: ignore
    ) as executor:

        def get_data(ride: Ride, app: Flask) -> None | pd.DataFrame:
            with app.app_context():
                this_track = ride.track
                if this_track:
                    return this_track.get_track_data()
                else:
                    return None

        future_datas = (
            executor.submit(
                get_data,
                ride,
                current_app._get_current_object(),  # type: ignore
            )
            for ride in rides
        )
        for future in concurrent.futures.as_completed(future_datas):
            data = future.result()
            if data is not None:
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


def generate_journal_month(month: int, year: int) -> list[JournalWeek]:
    first_in_month = date(year=year, month=month, day=1)

    next_month = month + 1
    next_month_year = year
    if next_month == 13:
        next_month = 1
        next_month_year = year + 1
    last_in_month = date(year=next_month_year, month=next_month, day=1) - timedelta(
        days=1
    )

    all_days_in_month: list[date] = []
    day = first_in_month
    while day != last_in_month:
        all_days_in_month.append(day)
        day = day + timedelta(days=1)
    all_days_in_month.append(day)

    first_week = all_days_in_month[0].isocalendar().week
    last_week = all_days_in_month[-1].isocalendar().week
    weeks_numbers = []
    for d in all_days_in_month:
        week_nr = d.isocalendar().week
        if week_nr not in weeks_numbers:
            weeks_numbers.append(week_nr)

    logger.debug("First week: %s | Last Week %s", first_week, last_week)
    days_in_week: Dict[int, list[JournalDay]] = {i: [] for i in weeks_numbers}

    for day in all_days_in_month:
        days_in_week[day.isocalendar().week].append(
            JournalDay(
                date=day,
                name=weekday_map[day.isocalendar().weekday],
                in_month=True,
                highlight_day=day == date.today(),
            )
        )
    if len(days_in_week[first_week]) != 7:
        while len(days_in_week[first_week]) < 7:
            add_day = days_in_week[first_week][0].date - timedelta(days=1)

            days_in_week[first_week].insert(
                0,
                JournalDay(
                    date=add_day,
                    name=weekday_map[add_day.isocalendar().weekday],
                    in_month=False,
                    highlight_day=add_day == date.today(),
                ),
            )

    if len(days_in_week[last_week]) != 7:
        while len(days_in_week[last_week]) < 7:
            add_day = days_in_week[last_week][-1].date + timedelta(days=1)
            days_in_week[last_week].append(
                JournalDay(
                    date=add_day,
                    name=weekday_map[add_day.isocalendar().weekday],
                    in_month=False,
                    highlight_day=add_day == date.today(),
                ),
            )

    return [
        JournalWeek(week=week, days=tuple(days))  # type: ignore
        for week, days in days_in_week.items()
    ]


@bp.route("/journal", methods=("GET", "POST"))
def journal() -> str:
    config = current_app.config

    today = datetime.now()
    month = today.month
    year = today.year

    overview_form = JournalForm()
    type_choices = ["All"] + config.adders.ride.type_choices

    overview_form.ride_type.choices = [
        ("Default", " , ".join(config.overview.default_types))
    ] + [(c, c) for c in type_choices]

    curr_year = date.today().year
    overview_form.year.choices = [(str(curr_year), str(curr_year))] + [
        (str(y), str(y)) for y in get_ride_years_in_database() if y != curr_year
    ]

    select_ride_types_ = overview_form.ride_type.data
    if select_ride_types_ == "Default":
        select_ride_types = config.overview.default_types
    else:
        select_ride_types = select_ride_types_

    # Deal with prev and next buttons
    button_used = False
    if request.method == "POST":
        if request.form.get("next_month", None) == "next_month":
            logger.debug("Next button pressed")
            curr_month = int(unwrap(request.form.get("curr_month")))
            curr_year = int(unwrap(request.form.get("curr_year")))
            button_used = True
            month = curr_month + 1
            year = int(curr_year)
            if month == 13:
                month = 1
                year = curr_year + 1

        if request.form.get("prev_month", None) == "prev_month":
            logger.debug("Prev button pressed")
            curr_month = int(unwrap(request.form.get("curr_month")))
            curr_year = int(unwrap(request.form.get("curr_year")))
            button_used = True
            month = curr_month - 1
            year = int(curr_year)
            if month == 0:
                month = 12
                year = curr_year - 1

        if request.form.get("today", None) == "today":
            today = datetime.now()
            month = today.month
            year = today.year

        logger.debug("After press: %s / %s", month, year)

    # Deal with form
    if overview_form.validate_on_submit() and not button_used:
        logger.debug("Form submitted")
        year, month = int(overview_form.year.data), int(overview_form.month.data)
        logger.debug("Data in form: %s / %s", month, year)

    present_categories_: list[str] = []

    weeks = generate_journal_month(month, year)

    ride_type_btn_class_map = {}
    last_btn_class_add = None
    for week in weeks:
        week_data = convert_ride_overview_container_to_df(
            get_ride_and_latest_track_overview(
                week.get_date_range(), ride_type=select_ride_types
            )
        )
        total_distance = 0
        total_duration = 0
        total_uphill = 0
        total_downhill = 0

        for row in week_data.to_dict("records"):
            for day in week.days:
                if day.date == row["date"]:
                    this_ride_type = row["ride_type"]
                    if this_ride_type not in ride_type_btn_class_map:
                        if (
                            last_btn_class_add is None
                            or last_btn_class_add == category_btn_classes[-1]
                        ):
                            next_btn_class = category_btn_classes[0]
                        else:
                            next_btn_class = category_btn_classes[
                                category_btn_classes.index(last_btn_class_add) + 1
                            ]
                        last_btn_class_add = copy(next_btn_class)
                        ride_type_btn_class_map[this_ride_type] = next_btn_class
                        logger.debug(
                            "Adding %s as btn class for category id %s",
                            next_btn_class,
                            this_ride_type,
                        )
                    if this_ride_type not in present_categories_:
                        present_categories_.append(this_ride_type)
                    ride_cat_btn_class = ride_type_btn_class_map[this_ride_type]
                    if not day.in_month:
                        ride_cat_btn_class = ride_cat_btn_class.replace(
                            "btn-", "btn-outline-"
                        )

                    total_distance += row["distance"]
                    total_duration += row["total_time"]
                    if row["uphill"] is not None:
                        total_uphill += row["uphill"]
                    if row["downhill"] is not None:
                        total_downhill += row["downhill"]

                    day.rides.append(
                        JournalRide(
                            id_ride=row["id_ride"],
                            duration=format_timedelta(
                                pd.Timedelta(seconds=row["total_time"])
                            ),
                            distance=f"{row['distance']:0.2f} km",
                            uphill=None
                            if (row["uphill"] is None or np.isnan(row["uphill"]))
                            else f"{int(row['uphill'])} m",
                            downhill=None
                            if (row["downhill"] is None or np.isnan(row["downhill"]))
                            else f"{int(row['downhill'])} m",
                            avg_velocity=None
                            if (
                                row["avg_velocity"] is None
                                or np.isnan(row["avg_velocity"])
                            )
                            else f"{int(row['avg_velocity']):0.2f} km/h",
                            btn_class=ride_cat_btn_class,
                        )
                    )
                    break

        if total_distance > 0:
            week.summary = JournalWeekSummary(
                distance=f"{total_distance:0.2f} km",
                duration=get_nice_timedelta_isoformat(
                    pd.Timedelta(seconds=total_duration).isoformat()
                ),
                uphill=f"{int(total_uphill)} m" if total_uphill > 0 else None,
                downhill=f"{int(total_downhill)} m" if total_downhill > 0 else None,
            )

    present_categories = [
        JournalCategory(name=cat, btn_class=ride_type_btn_class_map[cat])
        for cat in present_categories_
    ]

    overview_form.month.data = month
    overview_form.year.data = year
    return render_template(
        "journal.html",
        active_page="journal",
        month=month,
        year=year,
        overview_form=overview_form,
        weeks=weeks,
        present_categories=present_categories,
    )
