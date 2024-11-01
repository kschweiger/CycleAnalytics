import logging
from copy import deepcopy
from dataclasses import asdict
from typing import Literal, Type

import pandas as pd
from geo_track_analyzer import Track
from geo_track_analyzer.model import SegmentOverview

from ..model.base import RideOverviewContainer
from ..model.goal import AggregationType, Goal
from ..utils.base import compare_values
from .model import (
    DatabaseGoal,
    Ride,
    TrackOverview,
)

logger = logging.getLogger(__name__)


def convert_rides_to_df(rides: list[Ride]) -> pd.DataFrame:
    data = {
        "id_ride": [],
        "ride_type": [],
        "date": [],
        "distance": [],
        "total_time": [],
        "ride_time": [],
        "bike": [],
        "moving_time_seconds": [],
        "total_time_seconds": [],
        "moving_distance": [],
        "total_distance": [],
        "max_velocity": [],
        "avg_velocity": [],
        "max_elevation": [],
        "min_elevation": [],
        "uphill_elevation": [],
        "downhill_elevation": [],
        "moving_distance_km": [],
        "total_distance_km": [],
        "max_velocity_kmh": [],
        "avg_velocity_kmh": [],
        "bounds_min_lat": [],
        "bounds_max_lat": [],
        "bounds_min_lng": [],
        "bounds_max_lng": [],
    }
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

    for ride in rides:
        data["id_ride"].append(ride.id)
        data["date"].append(ride.ride_date)
        data["distance"].append(ride.distance)
        data["ride_type"].append(ride.terrain_type.text)
        data["total_time"].append(ride.total_duration)
        data["ride_time"].append(ride.ride_duration)
        data["bike"].append(ride.bike.name)
        try:
            overview = ride.track_overview
        except RuntimeError:
            overview = None

        for key in [
            key
            for key in data
            if key
            not in [
                "distance",
                "date",
                "id_ride",
                "ride_type",
                "total_time",
                "ride_time",
                "bike",
            ]
        ]:
            if overview is None:
                if key == "total_time_seconds":
                    data[key].append(ride.total_duration.seconds)
                elif key == "moving_time_seconds" and ride.ride_duration is not None:
                    data[key].append(ride.ride_duration.seconds)
                else:
                    data[key].append(None)
            else:
                data[key].append(getattr(overview, key))

    data_df = pd.DataFrame(data)
    if not data_df.empty:
        data_df["year"] = data_df.apply(lambda r: r.date.year, axis=1)
        data_df["month"] = data_df.apply(lambda r: month_labels[r.date.month], axis=1)

    return data_df


def summarize_rides_in_year(data: pd.DataFrame) -> list[tuple[str, str]]:
    # data = convert_rides_to_df(rides)
    if data.empty:
        summary_data_ = {
            "tot_distance": 0,
            "tot_time": "-",
            "num_rides": 0,
            "avg_distance": 0,
            "avg_ride_duration": "-",
        }
    else:
        summary_data_ = {
            "tot_distance": str(round(data.distance.sum(), 2)),
            "tot_time": str(pd.Timedelta(seconds=data.ride_time.sum())).split(".")[0],
            "num_rides": str(len(data)),
            "avg_distance": str(round(data.distance.mean(), 2)),
            "avg_ride_duration": str(pd.Timedelta(seconds=data.ride_time.mean()))
            .split(".")[0]
            .replace("0 days ", ""),
        }

    return [
        ("Total Distance [km]", summary_data_["tot_distance"]),
        ("Total Ride time ", summary_data_["tot_time"]),
        ("Number of rides", summary_data_["num_rides"]),
        ("Avg. distance [km]", summary_data_["avg_distance"]),
        (
            "Avg. ride duration",
            summary_data_["avg_ride_duration"],
        ),
    ]


def summarize_rides_in_month(
    curr_month_data: pd.DataFrame,
    last_month_data: pd.DataFrame,
    # rides_curr_month: list[Ride], rides_prev_month: list[Ride]
) -> list[tuple[str, float | pd.Timedelta, Literal[-1, 0, 1]]]:
    # curr_month_data = convert_rides_to_df(rides_curr_month)
    # last_month_data = convert_rides_to_df(rides_prev_month)

    curr_month_distance = curr_month_data.distance.sum()
    last_month_distance = last_month_data.distance.sum()

    _curr_month_ride_time = curr_month_data.ride_time.sum()
    _last_month_ride_time = last_month_data.ride_time.sum()
    curr_month_ride_time = pd.Timedelta(seconds=_curr_month_ride_time)
    last_month_ride_time = pd.Timedelta(seconds=_last_month_ride_time)
    curr_month_count = len(curr_month_data)
    last_month_count = len(last_month_data)

    return [
        (
            "Distance [km]",
            round(curr_month_distance, 2),
            compare_values(curr_month_distance - last_month_distance, 5),
        ),
        (
            "Ride time",
            curr_month_ride_time,
            compare_values(
                curr_month_ride_time - last_month_ride_time,  # type: ignore
                pd.Timedelta(minutes=15),  # type: ignore
            ),
        ),
        (
            "Rides",
            curr_month_count,
            compare_values(curr_month_count - last_month_count, 1),
        ),
    ]


def convert_database_goals(data: list[DatabaseGoal]) -> list[Goal]:
    from cycle_analytics.model.goal import GoalType, LocationGoal, ManualGoal, RideGoal

    def generate_goals(goal_type: Type[Goal], data: dict) -> list[Goal]:
        goals = []
        if data["month"] == 0:
            for i in range(1, 13):
                _data = deepcopy(data)
                _data["month"] = i
                goals.append(goal_type(**_data))
        else:
            goals.append(goal_type(**data))

        return goals

    goals: list[Goal] = []

    for db_goal in data:
        goal_dict = asdict(db_goal)
        goal_dict["aggregation_type"] = AggregationType(goal_dict["aggregation_type"])
        _type = GoalType(goal_dict.pop("goal_type"))
        if _type == GoalType.RIDE:
            goals.extend(generate_goals(RideGoal, goal_dict))
        elif _type == GoalType.MANUAL:
            goals.extend(generate_goals(ManualGoal, goal_dict))
        elif _type == GoalType.LOCATION:
            goals.extend(generate_goals(LocationGoal, goal_dict))
        else:
            raise NotImplementedError

    return goals


def track_to_db_overview(
    overview: SegmentOverview,
    id_track: None | int,
    id_segment: None | int,
    bounds: tuple[float, float, float, float],
) -> TrackOverview:
    min_lat, max_lat, min_lng, max_lng = bounds
    data = dict(
        id_segment=id_segment,
        moving_time_seconds=overview.moving_time_seconds,
        total_time_seconds=overview.total_time_seconds,
        moving_distance=overview.moving_distance,
        total_distance=overview.total_distance,
        max_velocity=overview.max_velocity,
        avg_velocity=overview.avg_velocity,
        max_elevation=overview.max_elevation,
        min_elevation=overview.min_elevation,
        uphill_elevation=overview.uphill_elevation,
        downhill_elevation=overview.downhill_elevation,
        moving_distance_km=overview.moving_distance_km,
        total_distance_km=overview.total_distance_km,
        max_velocity_kmh=overview.max_velocity_kmh,
        avg_velocity_kmh=overview.avg_velocity_kmh,
        bounds_min_lat=min_lat,
        bounds_max_lat=max_lat,
        bounds_min_lng=min_lng,
        bounds_max_lng=max_lng,
    )
    if id_track:
        data["id_track"] = id_track
    else:
        data["id_track"] = None
    return TrackOverview(**data)  # type: ignore


def initialize_overviews(
    track: Track,
    id_track: None | int = None,
) -> list[TrackOverview]:
    bounds = track.track.get_bounds()
    overviews = [
        track_to_db_overview(
            track.get_track_overview(),
            id_track,
            None,
            (
                bounds.min_latitude,
                bounds.max_latitude,
                bounds.min_longitude,
                bounds.max_longitude,
            ),  # type: ignore
        )
    ]
    if track.n_segments > 1:
        for i in range(track.n_segments):
            bounds = track.track.segments[i].get_bounds()
            overviews.append(
                track_to_db_overview(
                    track.get_segment_overview(i),
                    id_track,
                    i,
                    (
                        bounds.min_latitude,
                        bounds.max_latitude,
                        bounds.min_longitude,
                        bounds.max_longitude,
                    ),  # type: ignore
                )
            )

    return overviews


def convert_ride_overview_container_to_df(
    data: list[RideOverviewContainer],
) -> pd.DataFrame:
    data_dict = {
        "id_ride": [],
        "date": [],
        "year": [],
        "month": [],
        "distance": [],
        "ride_time": [],
        "total_time": [],
        "ride_type": [],
        "bike": [],
        "uphill": [],
        "downhill": [],
        "avg_velocity": [],
    }
    for row in data:
        data_dict["id_ride"].append(row.id_ride)
        data_dict["date"].append(row.ride_date.date())
        data_dict["year"].append(row.ride_date.year)
        data_dict["month"].append(row.ride_date.month)
        data_dict["distance"].append(row.distance_raw)
        data_dict["total_time"].append(row.total_duration.total_seconds())
        data_dict["ride_time"].append(
            row.total_duration.total_seconds()
            if row.ride_duration is None
            else row.ride_duration.total_seconds()
        )
        data_dict["ride_type"].append(row.terrain_type)
        data_dict["bike"].append(row.bike)
        data_dict["uphill"].append(
            0 if row.overview_uphill is None else row.overview_uphill
        )
        data_dict["downhill"].append(
            0 if row.overview_downhill is None else row.overview_downhill
        )
        data_dict["avg_velocity"].append(row.overview_avg_vel)

    return pd.DataFrame(data_dict)
