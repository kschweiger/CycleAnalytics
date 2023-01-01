import logging
from datetime import date, timedelta

import pandas as pd
from data_organizer.db.exceptions import QueryReturnedNoData
from gpx_track_analyzer.track import ByteTrack
from pandas import Timedelta
from pypika import Criterion, JoinType, Order, Table
from pypika.functions import Extract

from cycle_analytics.cache import cache
from cycle_analytics.db import get_db
from cycle_analytics.goals import Goal, initialize_goals
from cycle_analytics.model import LastRide
from cycle_analytics.plotting import convert_fig_to_base64, get_track_thumbnails
from cycle_analytics.utils import compare_values, get_nice_timedelta_isoformat

logger = logging.getLogger(__name__)


def get_last_ride(ride_type: str) -> LastRide:
    """
    Load the data of the latest ride from the database

    :param ride_type: _description_
    """
    last_id = get_last_id("main", "date", True)

    data = get_full_ride_data(last_id)
    last_ride_data = {
        "Distance [km]": data["distance"],
        "Duration": get_nice_timedelta_isoformat(data["total_time"].isoformat()),
    }
    if data["id_segment"] is not None:
        last_ride_data.update(
            {
                "Avg. Velocity [km/h]": round(data["avg_velocity_kmh"], 2),
                "Elevation Uphill [m]": round(data["uphill_elevation"], 2),
                "Elevation Downhill [m]": round(data["downhill_elevation"], 2),
            }
        )
    try:
        thumbnails = get_thumbnails_for_id(last_id)
    except QueryReturnedNoData:
        thumbnails = []

    return LastRide(date=data["date"], data=last_ride_data, thumbnails=thumbnails)


def get_last_id(table: str, order_by: str, descending: bool) -> int:
    db = get_db()

    query = (
        db.pypika_query.from_(Table(table))
        .select("id_ride")
        .orderby(order_by, order=Order.desc if descending else Order.asc)
        .limit(1)
    )

    return db.query(query)[0][0]


@cache.memoize(timeout=86400)
def get_full_ride_data(id_ride: int) -> pd.DataFrame:

    db = get_db()
    logger.debug("Getting id_ride %s", id_ride)
    main = Table("main")
    tracks = Table("tracks_enhanced_v1")
    track_data = Table("tracks_v1_overview")
    query = (
        db.pypika_query.from_(main)
        .join(tracks, how=JoinType.left)
        .on_field("id_ride")
        .join(track_data, how=JoinType.left)
        .on(tracks.id_track == track_data.id_track)
        .select(main.star, track_data.star)
        .where(main.id_ride == id_ride)
    )

    data = db.query_to_df(query).iloc[0]

    return data


@cache.memoize(timeout=86400)
def get_track_for_id(id_ride: int) -> ByteTrack:
    db = get_db()
    tracks = Table("tracks_enhanced_v1")
    query = (
        db.pypika_query.from_(tracks)
        .select(tracks.gpx)
        .where(tracks.id_ride == id_ride)
    )

    data = db.query(query)[0][0]

    return ByteTrack(bytes(data), 0)


@cache.memoize(timeout=86400)
def get_thumbnails_for_id(id_ride: int) -> list[str]:
    track = get_track_for_id(id_ride)
    return convert_fig_to_base64(
        get_track_thumbnails(track.get_segment_data()), 400, 400
    )


@cache.memoize(timeout=86400)
def get_rides_in_timeframe(timeframe: int | str | list[int]) -> pd.DataFrame:
    db = get_db()
    main = Table("main")
    tracks = Table("tracks_enhanced_v1")
    track_data = Table("tracks_v1_overview")
    query = (
        db.pypika_query.from_(main)
        .join(tracks, how=JoinType.left)
        .on_field("id_ride")
        .join(track_data, how=JoinType.left)
        .on(tracks.id_track == track_data.id_track)
        .select(main.star, track_data.star)
    )

    if timeframe == "All" or timeframe == "Any":
        logger.debug("Will not constrain rides to dates")
    elif isinstance(timeframe, list):
        query = query.where(
            Criterion.any(
                [
                    (main.date <= f"{year}-12-31") & (main.date >= f"{year}-01-01")
                    for year in timeframe
                ]
            )
        )
    else:
        year = int(timeframe)

        query = query.where(main.date <= f"{year}-12-31").where(
            main.date >= f"{year}-01-01"
        )

    data = db.query_to_df(query)

    month_labels = {
        1: "Jan",
        2: "Feb",
        3: "Mar",
        4: "Apr",
        5: "Mai",
        6: "Jun",
        7: "Jul",
        8: "Aug",
        9: "Sep",
        10: "Oct",
        11: "Nov",
        12: "Dec",
    }
    data["year"] = data.apply(lambda r: r.date.year, axis=1)
    data["month"] = data.apply(lambda r: month_labels[r.date.month], axis=1)

    print(data.columns)
    return data


def get_years_in_database() -> list[int]:
    db = get_db()

    main = Table("main")
    query = db.pypika_query.from_(main).select(Extract("year", main.date)).distinct()

    return [r[0] for r in db.query(query)]


def get_summary_data(timeframe: int | str, current_year: int, curr_month: int):

    try:
        rides = get_rides_in_timeframe(timeframe)
    except QueryReturnedNoData:
        summary_data_ = {
            "tot_distance": 0,
            "tot_time": "-",
            "num_rides": 0,
            "avg_distance": 0,
            "avg_ride_duration": "-",
        }
        rides = pd.DataFrame()
    else:
        summary_data_ = {
            "tot_distance": str(round(rides.distance.sum(), 2)),
            "tot_time": str(rides.ride_time.sum()).split(".")[0],
            "num_rides": str(len(rides)),
            "avg_distance": str(round(rides.distance.mean(), 2)),
            "avg_ride_duration": str(rides.ride_time.mean())
            .split(".")[0]
            .replace("0 days ", ""),
        }

    curr_month_start = date(current_year, curr_month, 1)
    if curr_month == 12:
        curr_month_end = date(current_year + 1, 1, 1) - timedelta(days=1)
    else:
        curr_month_end = date(current_year, curr_month + 1, 1) - timedelta(days=1)

    if curr_month == 1:
        last_year = curr_month_start.year - 1
        last_month_start = date(last_year, 12, 1)
        last_month_end = date(last_year, 12, 31)
    else:
        last_month_end = curr_month_start - timedelta(days=1)
        last_month_start = date(last_month_end.year, last_month_end.month, 1)

    logger.debug("Curr. month:  %s - %s", curr_month_start, curr_month_end)
    logger.debug("Last month:  %s - %s", last_month_start, last_month_end)

    if curr_month == 1:
        logger.debug("Loading data from previous timeframe")
        prev_year_rides = get_rides_in_timeframe(current_year - 1)
        last_month_data = prev_year_rides[
            (prev_year_rides.date >= last_month_start)
            & (prev_year_rides.date <= last_month_end)
        ]
        if rides.empty:
            rides = prev_year_rides
        else:
            rides = pd.concat([rides, prev_year_rides])
    else:
        last_month_data = rides[
            (rides.date >= last_month_start) & (rides.date <= last_month_end)
        ]

    if rides.empty:
        summary_month = []
    else:
        curr_month_data = rides[
            (rides.date >= curr_month_start) & (rides.date <= curr_month_end)
        ]

        curr_month_distance = curr_month_data.distance.sum()
        last_month_distance = last_month_data.distance.sum()

        curr_month_ride_time = curr_month_data.ride_time.sum()
        last_month_ride_time = last_month_data.ride_time.sum()

        curr_month_count = len(curr_month_data)
        last_month_count = len(last_month_data)

        summary_month = [
            (
                "Distance [km]",
                curr_month_distance,
                compare_values(curr_month_distance - last_month_distance, 5),
            ),
            (
                "Ride time",
                curr_month_ride_time,
                compare_values(
                    curr_month_ride_time - last_month_ride_time, Timedelta(minutes=15)
                ),
            ),
            (
                "Rides",
                curr_month_count,
                compare_values(curr_month_count - last_month_count, 1),
            ),
        ]

    summary_data = [
        ("Total Distance [km]", summary_data_["tot_distance"]),
        ("Total Ride time ", summary_data_["tot_time"]),
        ("Number of rides", summary_data_["num_rides"]),
        ("Avg. distance [km]", summary_data_["avg_distance"]),
        (
            "Avg. ride duration",
            summary_data_["avg_ride_duration"],
        ),
    ]

    return summary_data, summary_month


@cache.memoize(timeout=86400)
def load_goals(year: int | str) -> list[Goal]:
    db = get_db()
    table_goals = Table("goals")
    query = db.pypika_query.from_(table_goals).select("*")
    try:
        query = query.where(table_goals.year == int(year))
    except ValueError:
        if year not in ["All", "Any"]:
            raise ValueError(f"Year {year} not supported")

    data, columns = db.query_inc_keys(query=query)

    return initialize_goals(columns, data)


@cache.memoize(timeout=86400)
def get_goal_years() -> list[int]:
    db = get_db()
    table_goals = Table("goals")
    query = db.pypika_query.from_(table_goals).select(table_goals.year).distinct()

    data = db.query(query)

    return [y[0] for y in data]
