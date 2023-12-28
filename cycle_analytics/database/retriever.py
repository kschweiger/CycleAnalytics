import logging
from datetime import date
from typing import Type

from sqlalchemy import and_, func, or_, select

from .model import CategoryModel, Ride, TerrainType, db

logger = logging.getLogger(__name__)


def get_years_in_database() -> list[int]:
    """Get a list of all years present in ride dates"""
    distinct_years = (
        db.session.query(func.extract("year", Ride.ride_date)).distinct().all()
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
        timeframe = get_years_in_database()

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
