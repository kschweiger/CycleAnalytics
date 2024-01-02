import logging
from datetime import date, timedelta
from typing import Any, Dict, Optional, Tuple

import pandas as pd

# import psycopg2
# from data_organizer.db.exceptions import QueryReturnedNoData
from pandas import Timedelta
from pypika import Criterion, JoinType, Order, Table
from pypika.functions import Count, Extract, Max, Min, Sum
from track_analyzer.track import ByteTrack

from cycle_analytics.cache import cache
from cycle_analytics.db import get_db
from cycle_analytics.model.base import (
    Bike,
    LastRide,
    LatLngBounds,
    SegmentData,
    bike_from_dict,
)
from cycle_analytics.model.goal import Goal, initialize_goals
from cycle_analytics.plotting import convert_fig_to_base64, get_track_thumbnails
from cycle_analytics.rest_models import SegmentForMap
from cycle_analytics.utils import (
    compare_values,
    get_date_range_from_year_month,
    get_nice_timedelta_isoformat,
)

logger = logging.getLogger(__name__)


def get_bike_names() -> list[str]:
    db = get_db()
    tables = Table("bikes")
    query = db.pypika_query.from_(tables).select(tables.bike_name).distinct()
    bikes = db.query(query)

    return [b[0] for b in bikes]


def get_full_bike_date(bike_name: str) -> Bike:
    db = get_db()
    bikes = Table("bikes")
    query = db.pypika_query.from_(bikes).select("*").where(bikes.bike_name == bike_name)

    data, keys = db.query_inc_keys(query)

    return bike_from_dict({key: value for key, value in zip(keys, data[0])})


def get_agg_data_for_bike(bike_name: str) -> None | Dict[str, Any]:
    db = get_db()
    main = Table("main")

    query = (
        db.pypika_query.from_(main)
        .select(
            Count("*").as_("rides"),
            Sum(main.distance).as_("total_distance"),
            Sum(main.total_time).as_("total_time"),
            Min(main.date).as_("first_ride"),
            Max(main.date).as_("last_ride"),
        )
        .where(main.bike == bike_name)
    )

    try:
        data, keys = db.query_inc_keys(query)
    except QueryReturnedNoData:
        return None

    agg_data = {key: value for key, value in zip(keys, data[0])}
    agg_data["total_distance"] = round(agg_data["total_distance"], 2)
    return agg_data


def get_last_ride(ride_type: None | str) -> None | LastRide:
    """
    Load the data of the latest ride from the database

    :param ride_type: _description_
    """
    try:
        last_id = get_last_id("main", "date", True, ride_type)
    except QueryReturnedNoData:
        return None

    data = get_full_ride_data(last_id)
    last_ride_data = {
        "Distance [km]": data["distance"],
        "Duration": get_nice_timedelta_isoformat(data["total_time"].isoformat()),
    }
    if data["avg_velocity_kmh"] is not None:
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

    return LastRide(
        id=last_id, date=data["date"], data=last_ride_data, thumbnails=thumbnails
    )


def get_last_id(
    table: str, order_by: str, descending: bool, ride_type: None | str
) -> int:
    db = get_db()

    query = (
        db.pypika_query.from_(Table(table))
        .select("id_ride")
        .orderby(order_by, order=Order.desc if descending else Order.asc)
        .limit(1)
    )

    if ride_type is not None:
        query = query.where(Table(table).ride_type == ride_type)

    return db.query(query)[0][0]


def get_last_track_id(table: str, order_by: str, descending: bool) -> int:
    db = get_db()

    query = (
        db.pypika_query.from_(Table(table))
        .select("id_track")
        .orderby(order_by, order=Order.desc if descending else Order.asc)
        .limit(1)
    )

    return db.query(query)[0][0]


# @cache.memoize(timeout=86400)
def get_full_ride_data(id_ride: int) -> pd.DataFrame:
    db = get_db()
    logger.debug("Getting id_ride %s", id_ride)
    main = Table("main")
    tracks = Table("tracks_enhanced_v1")
    track_data = Table("tracks_v1_overview")
    notes = Table("ride_notes")
    query = (
        db.pypika_query.from_(main)
        .join(tracks, how=JoinType.left)
        .on_field("id_ride")
        .join(track_data, how=JoinType.left)
        .on(tracks.id_track == track_data.id_track)
        .join(notes, how=JoinType.left)
        .on(main.id_ride == notes.id_ride)
        .select(main.star, track_data.star, notes.note)
        .where(main.id_ride == id_ride)
    )
    return db.query_to_df(query).iloc[0]


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


def get_track(id_track: int) -> ByteTrack:
    return ByteTrack(get_track_data(id_track), 0)


@cache.memoize(timeout=86400)
def get_track_data(id_track: int, table_name: str = "tracks_enhanced_v1") -> bytes:
    db = get_db()
    tracks = Table(table_name)
    query = (
        db.pypika_query.from_(tracks)
        .select(tracks.gpx)
        .where(tracks.id_track == id_track)
    )

    data = db.query(query)[0][0]

    return bytes(data)


def ride_has_track(id_ride: int, table_name: str) -> bool:
    data = ride_track_id(id_ride, table_name)
    if data is None:
        return False
    else:
        return True


def ride_track_id(id_ride: int, table_name: str) -> None | int:
    db = get_db()
    tracks = Table(table_name)
    query = (
        db.pypika_query.from_(tracks)
        .select(tracks.id_track)
        .where(tracks.id_ride == id_ride)
    )
    try:
        data = db.query(query)
    except QueryReturnedNoData:
        return None

    return data[0][0]


def ride_track_ids(id_ride: int, table_name: str) -> None | list[int]:
    db = get_db()
    tracks = Table(table_name)
    query = (
        db.pypika_query.from_(tracks)
        .select(tracks.id_track)
        .where(tracks.id_ride == id_ride)
    )
    try:
        data = db.query(query)
    except QueryReturnedNoData:
        return None

    return list(data[0])


@cache.memoize(timeout=86400)
def get_thumbnails_for_id(id_ride: int) -> list[str]:
    track = get_track_for_id(id_ride)
    return convert_fig_to_base64(
        get_track_thumbnails(track.get_segment_data()), 400, 400
    )


@cache.memoize(timeout=86400)
def get_rides_in_timeframe(
    timeframe: int | str | list[int] | tuple[date, date],
    ride_type: str | list[str] = "Any",
) -> pd.DataFrame:
    db = get_db()
    main = Table("main")
    tracks = Table("tracks_enhanced_v1")
    track_data = Table("tracks_v1_overview")
    query = (
        db.pypika_query.from_(main)
        .distinct_on(main.id_ride)
        .join(tracks, how=JoinType.left)
        .on_field("id_ride")
        .join(track_data, how=JoinType.left)
        .on(tracks.id_track == track_data.id_track)
        .select(main.star, track_data.star)
        .orderby(main.id_ride, tracks.id_track, order=Order.desc)
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

    elif isinstance(timeframe, tuple):
        start_date, end_date = timeframe
        query = query.where(
            Criterion.any([(main.date <= end_date) & (main.date >= start_date)])
        )
    else:
        year = int(timeframe)

        query = query.where(main.date <= f"{year}-12-31").where(
            main.date >= f"{year}-01-01"
        )

    if ride_type == "Any" or ride_type == "All":
        logger.debug("Will not constrain rides to a specific ride_type")
    else:
        if isinstance(ride_type, str):
            ride_type_ = [ride_type]
        else:
            ride_type_ = ride_type
        query = query.where(main.ride_type.isin(ride_type_))
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

    return data


def get_years_in_database() -> list[int]:
    db = get_db()

    main = Table("main")
    query = db.pypika_query.from_(main).select(Extract("year", main.date)).distinct()

    return [r[0] for r in db.query(query)]


def get_summary_data(
    timeframe: int | str, current_year: int, curr_month: int, ride_type: str = "Any"
) -> tuple[list, list]:
    try:
        rides = get_rides_in_timeframe(timeframe, ride_type=ride_type)
    except QueryReturnedNoData:
        summary_data_ = {
            "tot_distance": 0,
            "tot_time": "-",
            "num_rides": 0,
            "avg_distance": 0,
            "avg_ride_duration": "-",
        }
        rides = pd.DataFrame({"date": []})
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
        try:
            prev_year_rides = get_rides_in_timeframe(
                current_year - 1, ride_type=ride_type
            )
        except QueryReturnedNoData:
            prev_year_rides = pd.DataFrame({"date": []})

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
                round(curr_month_distance, 2),
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


# @cache.memoize(timeout=86400)
def load_goals(year: int | str, load_active: bool, load_inactive: bool) -> list[Goal]:
    db = get_db()
    table_goals = Table("goals")
    query = db.pypika_query.from_(table_goals).select("*")
    if load_active and not load_inactive:
        query = query.where(table_goals.active == True)  # noqa: E712
    if not load_active and load_inactive:
        query = query.where(table_goals.active == False)  # noqa: E712
    if not load_active and not load_inactive:
        return []
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


@cache.memoize(timeout=86400)
def get_event_years() -> list[int]:
    db = get_db()
    table_events = Table("events")
    query = (
        db.pypika_query.from_(table_events)
        .select(Extract("year", table_events.date))
        .distinct()
    )

    data = db.query(query)

    return [y[0] for y in data]


@cache.memoize(timeout=86400)
def get_events(
    year: Optional[int], month: Optional[int], event_types: Optional[list[str]]
) -> list[Dict[str, Any]]:
    logger.debug("Got Year/Month/event_type - %s/%s/%s", year, month, event_types)
    db = get_db()
    table_events = Table("events")
    query = db.pypika_query.from_(table_events).select("*")
    if year is None and month is not None:
        raise RuntimeError("Year can not be None if month is not None")

    if year is not None:
        query_date_start, query_date_end = get_date_range_from_year_month(year, month)

        query = query.where(table_events.date >= query_date_start).where(
            table_events.date <= query_date_end
        )

    if event_types is not None:
        query = query.where(table_events.event_type.isin(event_types))

    try:
        datas, keys = db.query_inc_keys(query)
    except QueryReturnedNoData:
        return {}  # type: ignore

    return [{key: value for key, value in zip(keys, data)} for data in datas]


def get_recent_events(
    n_max: int, constrain_type: Optional[str]
) -> list[Dict[str, Any]]:
    logger.debug("Getting %s event with type %s", n_max, constrain_type)
    db = get_db()
    table_events = Table("events")
    query = db.pypika_query.from_(table_events).select("*")
    if constrain_type is not None:
        query = query.where(table_events.event_type == constrain_type)

    query = query.orderby(table_events.date, order=Order.desc).limit(n_max)
    try:
        datas, keys = db.query_inc_keys(query)
    except QueryReturnedNoData:
        return {}  # type: ignore

    return [{key: value for key, value in zip(keys, data)} for data in datas]


def get_events_for_ride(id_ride: int) -> list[Dict[str, Any]]:
    db = get_db()
    table_events = Table("events")
    query = (
        db.pypika_query.from_(table_events)
        .select("*")
        .where(table_events.id_ride == id_ride)
    )
    try:
        datas, keys = db.query_inc_keys(query)
    except QueryReturnedNoData:
        return []

    return [{key: value for key, value in zip(keys, data)} for data in datas]


def modify_goal_status(id_goal: int, active: bool = True) -> bool:
    table = Table("goals")
    db = get_db()
    query = (
        db.pypika_query.update(table)
        .set(table.active, active)
        .where(table.id_goal == id_goal)
    )

    return db.exec_arbitrary(query)


def update_track(table_name: str, id_track: int, id_ride: int, track: bytes) -> bool:
    db = get_db()
    table = Table(table_name)
    query = (
        db.pypika_query.update(table)
        .set(table.gpx, psycopg2.Binary(track))
        .where(table.id_track == id_track)
        .where(table.id_ride == id_ride)
    )
    return db.exec_arbitrary(query)


def track_has_overview(id_track: int, table_name: str = "tracks_v1_overview") -> bool:
    db = get_db()
    table = Table(table_name)
    query = db.pypika_query.from_(table).select("*").where(table.id_track == id_track)
    try:
        db.query(query)
    except QueryReturnedNoData:
        return False

    return True


def update_track_overview(
    table_name: str,
    id_track: int,
    cols: list[str],
    data: list[int | float],
) -> bool:
    assert len(cols) == len(data)

    db = get_db()
    table = Table(table_name)
    query = db.pypika_query.update(table)
    for icol, col in enumerate(cols):
        query = query.set(table[col], data[icol])
    query = query.where(table.id_track == id_track)
    return db.exec_arbitrary(query)


def get_all_segments(difficulty_mapping: Optional[Dict[int, str]]) -> list[SegmentData]:
    db = get_db()
    table = Table("segments")
    query = db.pypika_query.from_(table).select(table.id_segment)
    datas, _ = db.query_inc_keys(query)

    segments = []
    for data in datas:
        segments.append(get_segment_data(next(iter(data)), difficulty_mapping))

    return segments


def get_segment_data(
    id_segment: int, difficulty_mapping: Optional[Dict[int, str]]
) -> SegmentData:
    db = get_db()
    table = Table("segments")
    query = (
        db.pypika_query.from_(table).select("*").where(table.id_segment == id_segment)
    )

    datas, keys = db.query_inc_keys(query)
    data = {key: value for key, value in zip(keys, datas[0])}

    return SegmentData(
        id=data["id_segment"],
        name=data["segment_name"],
        description=data["description"],
        distance=round(data["distance"], 2),
        visited=data["visited"],
        type=data["type"],
        difficulty=None
        if not difficulty_mapping
        else difficulty_mapping[data["difficulty"]],
        min_elevation=None
        if data["min_elevation"] is None
        else round(data["min_elevation"], 2),
        max_elevation=None
        if data["max_elevation"] is None
        else round(data["max_elevation"], 2),
        uphill_elevation=None
        if data["uphill_elevation"] is None
        else round(data["uphill_elevation"], 2),
        downhill_elevation=None
        if data["downhill_elevation"] is None
        else round(data["downhill_elevation"], 2),
        track=ByteTrack(bytes(data["gpx"]), 0),
        bounds=LatLngBounds(
            min_latitude=data["bounds_min_lat"],
            max_latitude=data["bounds_max_lat"],
            min_longitude=data["bounds_min_lng"],
            max_longitude=data["bounds_max_lng"],
        ),
    )


def get_segment_track(id_segment: int) -> Tuple[ByteTrack, str]:
    data = get_segment_data(id_segment=id_segment, difficulty_mapping=None)

    return data.track, data.name


def get_segments_for_map_in_bounds(
    ignore_ids: list[int],
    ne_lat: float,
    ne_lng: float,
    sw_lat: float,
    sw_lng: float,
    difficulty_mapping: Dict[int, str],
    color_typ_mappign: Dict[str, str],
    url_base: str,
) -> list[SegmentForMap]:
    table = Table("segments")
    db = get_db()

    query = (
        db.pypika_query.from_(table)
        .select("*")
        .where(
            (table.bounds_min_lat >= sw_lat)
            & (table.bounds_max_lat <= ne_lat)
            & (table.bounds_min_lng >= sw_lng)
            & (table.bounds_max_lng <= ne_lng)
        )
    )
    if ignore_ids:
        query = query.where(table.id_segment.notin(ignore_ids))

    segments_for_map = []

    datas, keys = db.query_inc_keys(query)
    for data in datas:
        segment_data = {key: value for key, value in zip(keys, data)}

        track = ByteTrack(bytes(segment_data["gpx"]), 0)

        segments_for_map.append(
            SegmentForMap(
                segment_id=segment_data["id_segment"],
                name=segment_data["segment_name"],
                points=[
                    (p.latitude, p.longitude) for p in track.track.segments[0].points
                ],
                url=url_base + str(segment_data["id_segment"]),
                type=segment_data["type"],
                difficulty=difficulty_mapping[segment_data["difficulty"]],
                color=color_typ_mappign[segment_data["type"]],
            )
        )

    return segments_for_map


def modify_segment_visited_flag(id_segment: int, visited: bool = True) -> bool:
    table = Table("segments")
    db = get_db()
    query = (
        db.pypika_query.update(table)
        .set(table.visited, visited)
        .where(table.id_segment == id_segment)
    )

    return db.exec_arbitrary(query)


def get_all_notes() -> list[tuple[int, str]]:
    db = get_db()
    ride_notes = Table("ride_notes")
    query = db.pypika_query.from_(ride_notes).select(
        ride_notes.id_ride, ride_notes.note
    )
    return db.query(query)


def get_note(id_ride: int) -> None | str:
    db = get_db()
    ride_notes = Table("ride_notes")
    query = (
        db.pypika_query.from_(ride_notes)
        .select(ride_notes.note)
        .where(ride_notes.id_ride == id_ride)
    )

    try:
        data = db.query(query)
    except QueryReturnedNoData:
        return None

    return data[0][0]


def modify_note(id_ride: int, note_value: str) -> bool:
    table = Table("ride_notes")
    db = get_db()
    query = (
        db.pypika_query.update(table)
        .set(table.note, note_value)
        .where(table.id_ride == id_ride)
    )

    return db.exec_arbitrary(query)


def get_ride_bounds() -> None | list[tuple[int, int, float, float, float, float]]:
    db = get_db()

    tre = Table("tracks_enhanced_v1")
    tro = Table("tracks_v1_overview")

    query = (
        db.pypika_query.from_(tre)
        .join(tro, how=JoinType.left)
        .on_field("id_track")
        .select(
            tre.id_ride,
            tre.id_track,
            tro.id_segment,
            tro.bounds_min_lat,
            tro.bounds_max_lat,
            tro.bounds_min_lng,
            tro.bounds_max_lng,
        )
    )

    try:
        data = db.query(query)
    except QueryReturnedNoData:
        return None

    return data


def get_rides_in_bounds(
    ne_lat: float, ne_lng: float, sw_lat: float, sw_lng: float
) -> None | list[tuple[int, int]]:
    db = get_db()

    tre = Table("tracks_enhanced_v1")
    tro = Table("tracks_v1_overview")

    query = (
        db.pypika_query.from_(tre)
        .join(tro, how=JoinType.left)
        .on_field("id_track")
        .select(tre.id_ride, tre.id_track)
        .where(
            (tro.bounds_min_lat <= sw_lat)
            & (tro.bounds_max_lat >= ne_lat)
            & (tro.bounds_min_lng <= sw_lng)
            & (tro.bounds_max_lng >= ne_lng)
        )
    )

    try:
        data = db.query(query)
    except QueryReturnedNoData:
        return None

    return data
