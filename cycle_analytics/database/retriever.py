import logging
from datetime import date, timedelta
from typing import Type

from sqlalchemy import and_, desc, func, or_, select
from track_analyzer import ByteTrack, Track

from cycle_analytics.cache import cache
from cycle_analytics.database.converter import convert_database_goals
from cycle_analytics.model.base import LastRide
from cycle_analytics.model.goal import Goal
from cycle_analytics.plotting import convert_fig_to_base64, get_track_thumbnails
from cycle_analytics.utils.base import (
    format_timedelta,
    get_date_range_from_year_month,
    none_or_round,
)

from .model import (
    CategoryModel,
    DatabaseEvent,
    DatabaseGoal,
    DatabaseTrack,
    EventType,
    Ride,
    TerrainType,
    db,
)

logger = logging.getLogger(__name__)


def get_ride_years_in_database() -> list[int]:
    """Get a list of all years present in ride dates"""
    distinct_years = (
        db.session.query(func.extract("year", Ride.ride_date)).distinct().all()
    )

    return [year[0] for year in distinct_years]


def get_goal_years_in_database() -> list[int]:
    """Get a list of all years present in goals"""
    distinct_years = db.session.query(DatabaseGoal.year).distinct().all()

    return [year[0] for year in distinct_years]


def get_event_years_in_database() -> list[int]:
    """Get a list of all years present in events"""
    distinct_years = (
        db.session.query(func.extract("year", DatabaseEvent.event_date))
        .distinct()
        .all()
    )

    return [year[0] for year in distinct_years]


def get_possible_values(category_model_type: Type[CategoryModel]) -> list[str]:
    """Get all possible value for a CategoryModel Mapping

    :param category_model_type: A child of CategoryModel model
    :return: List of all text values for the passed CategoryModel
    """
    return [c.text for c in category_model_type.query.all()]


def convert_to_indices(
    values: list[str], category_model_type: Type[CategoryModel]
) -> list[int]:
    relevant_elements = db.session.execute(
        select(category_model_type).where(category_model_type.text.in_(values))
    ).scalars()

    if not relevant_elements:
        raise RuntimeError  # FIXME

    return [e.id for e in relevant_elements]


def get_rides_in_timeframe(
    timeframe: int | str | list[int] | tuple[date, date],
    ride_type: str | list[str] = "Any",
) -> list[Ride]:
    if timeframe == "All" or timeframe == "Any":
        timeframe = get_ride_years_in_database()

    date_ranges: list[tuple[date, date]] = []
    if isinstance(timeframe, list):
        for year in timeframe:
            date_ranges.append((date(year, 1, 1), date(year, 12, 31)))

    elif isinstance(timeframe, tuple):
        date_ranges.append(timeframe)
    else:
        year = int(timeframe)
        date_ranges.append((date(year, 1, 1), date(year, 12, 31)))

    if ride_type == "Any" or ride_type == "All":
        ride_types = get_possible_values(TerrainType)
    else:
        if isinstance(ride_type, str):
            ride_types = [ride_type]
        else:
            ride_types = ride_type

    select_terrain_indices = convert_to_indices(ride_types, TerrainType)

    rides = (
        db.session.query(Ride)
        .filter(
            and_(
                Ride.id_terrain_type.in_(select_terrain_indices),
                or_(
                    *(
                        and_(
                            Ride.ride_date >= start_date,
                            Ride.ride_date <= end_date,
                        )
                        for start_date, end_date in date_ranges
                    )
                ),
            )
        )
        .all()
    )

    return rides


def get_curr_and_prev_month_rides(
    curr_year: int,
    curr_month: int,
    ride_type: str | list[str] = "Any",
) -> tuple[list[Ride], list[Ride]]:
    curr_month_start = date(curr_year, curr_month, 1)
    if curr_month == 12:
        curr_month_end = date(curr_year + 1, 1, 1) - timedelta(days=1)
    else:
        curr_month_end = date(curr_year, curr_month + 1, 1) - timedelta(days=1)

    if curr_month == 1:
        last_year = curr_month_start.year - 1
        last_month_start = date(last_year, 12, 1)
        last_month_end = date(last_year, 12, 31)
    else:
        last_month_end = curr_month_start - timedelta(days=1)
        last_month_start = date(last_month_end.year, last_month_end.month, 1)

    logger.debug("Curr. month:  %s - %s", curr_month_start, curr_month_end)
    logger.debug("Last month:  %s - %s", last_month_start, last_month_end)

    curr_month_rides = get_rides_in_timeframe(
        (curr_month_start, curr_month_end), ride_type
    )

    prev_month_rides = get_rides_in_timeframe(
        (last_month_start, last_month_end), ride_type
    )

    return curr_month_rides, prev_month_rides


@cache.memoize(timeout=86400)
def get_thumbnails_for_id(id_track: int) -> list[str]:
    track = ByteTrack(db.get_or_404(DatabaseTrack, id_track).content)
    return convert_fig_to_base64(
        get_track_thumbnails(track.get_segment_data()), 400, 400
    )


def get_thumbnails(track: Track) -> list[str]:
    return convert_fig_to_base64(
        get_track_thumbnails(track.get_segment_data()), 400, 400
    )


def get_last_ride(ride_type: None | str) -> None | LastRide:
    sel = select(Ride).order_by(desc(Ride.ride_date))
    if ride_type is not None:
        ride_type_id = convert_to_indices([ride_type], TerrainType)[0]
        sel = sel.filter(Ride.id_terrain_type == ride_type_id)
    ride = db.session.execute(sel).scalar()

    if ride is None:
        return None

    last_ride_data = {
        "Distance [km]": ride.distance,
        "Duration": format_timedelta(ride.total_duration),
    }
    try:
        overview = ride.track_overview
    except RuntimeError:
        overview = None

    if overview:
        last_ride_data.update(
            {
                "Avg. Velocity [km/h]": round(overview.avg_velocity_kmh, 2),
                "Elevation Uphill [m]": none_or_round(overview.uphill_elevation),
                "Elevation Downhill [m]": none_or_round(overview.downhill_elevation),
            }
        )

    thumbnails = None
    track = ride.track
    if track:
        thumbnails = get_thumbnails(track)

    return LastRide(
        id=ride.id,
        date=ride.ride_date,
        data=last_ride_data,
        thumbnails=thumbnails,  # thumbnails
    )


def get_recent_events(limit: int, select_event_type: None | str) -> list[DatabaseEvent]:
    sel = select(DatabaseEvent).order_by(desc(DatabaseEvent.event_date)).limit(limit)
    if select_event_type:
        select_event_type_id = convert_to_indices([select_event_type], EventType)[0]
        sel = sel.filter(DatabaseEvent.id_event_type == select_event_type_id)

    return list(db.session.execute(sel).scalars())


@cache.memoize(timeout=86400)
def get_events(
    year: None | int, month: None | int, event_types: None | list[str]
) -> list[DatabaseEvent]:
    logger.debug("Got Year/Month/event_type - %s/%s/%s", year, month, event_types)

    sel = select(DatabaseEvent).order_by(desc(DatabaseEvent.event_date))
    if year is None and month is not None:
        raise RuntimeError("Year can not be None if month is not None")

    _filters = []
    if year is not None:
        query_date_start, query_date_end = get_date_range_from_year_month(year, month)
        _filters.extend(
            [
                DatabaseEvent.event_date >= query_date_start,
                DatabaseEvent.event_date <= query_date_end,
            ]
        )
    if event_types is not None:
        event_type_idx = convert_to_indices(event_types, EventType)
        _filters.append(DatabaseEvent.id_event_type.in_(event_type_idx))

    if _filters:
        sel = sel.filter(and_(*_filters))

    return list(db.session.execute(sel).scalars())


def load_goals(year: int | str, load_active: bool, load_inactive: bool) -> list[Goal]:
    sel = select(DatabaseGoal)
    _filters = []
    try:
        _filters.append(DatabaseGoal.year == int(year))
    except ValueError:
        if year not in ["All", "Any"]:
            raise ValueError(f"Year {year} not supported")

    if load_active and not load_inactive:
        _filters.append(DatabaseGoal.active == True)
    if not load_active and load_inactive:
        _filters.append(DatabaseGoal.active == False)
    if not load_active and not load_inactive:
        return []

    sel = sel.filter(*_filters)

    return convert_database_goals(list(db.session.execute(sel).scalars()))


@cache.memoize(timeout=86400)
def get_rides_for_bike(id_bike: int) -> list[Ride]:
    return list(
        db.session.execute(select(Ride).filter_by(Ride.id_bike == id_bike)).scalars()
    )


def get_agg_data_for_bike(id_bike: int):
    result = (
        db.session.query(
            func.count().label("Number of rides"),
            func.sum(Ride.distance).label("Total distance [km]"),
            func.sum(Ride.total_duration).label("Total time "),
            func.min(Ride.ride_date).label("Date of first ride"),
            func.max(Ride.ride_date).label("Date of last ride"),
        )
        .filter(Ride.id_bike == id_bike)
        .first()
    )

    if result:
        res_dict = result._asdict()
        if res_dict["Total distance [km]"]:
            res_dict["Total distance [km]"] = round(res_dict["Total distance [km]"], 2)
        return res_dict

    return None
