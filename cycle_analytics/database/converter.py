import logging
from dataclasses import asdict
from datetime import datetime, timedelta

import pandas as pd
from flask import current_app
from flask_sqlalchemy import SQLAlchemy
from track_analyzer import Track
from track_analyzer.model import SegmentOverview

from cycle_analytics.model.goal import Goal
from cycle_analytics.utils.base import compare_values

from .model import (
    Bike,
    DatabaseEvent,
    DatabaseGoal,
    DatabaseSegment,
    DatabaseTrack,
    Difficulty,
    EventType,
    Material,
    Ride,
    RideNote,
    SegmentType,
    TerrainType,
    TrackOverview,
    TypeSpecification,
)

logger = logging.getLogger(__name__)


def convert_data(database: SQLAlchemy):
    from cycle_analytics.queries import (
        get_all_notes,
        get_all_segments,
        get_bike_names,
        get_events,
        get_full_bike_date,
        get_rides_in_timeframe,
        get_track_data,
        ride_has_track,
        ride_track_ids,
    )

    bikes = {}
    for name in get_bike_names():
        data = get_full_bike_date(name)
        bikes[name] = Bike(
            name=data.name,
            brand=data.brand,
            model=data.model,
            weight=data.weight,
            commission_date=data.purchased,
            decommission_date=data.decommissioned,
            id_material=database.session.execute(
                database.select(Material).filter_by(text=data.material.capitalize())
            )
            .scalar_one()
            .id,
            id_terraintype=database.session.execute(
                database.select(TerrainType).filter_by(text="MTB")
            )
            .scalar_one()
            .id,
            id_specification=database.session.execute(
                database.select(TypeSpecification).filter_by(
                    text=data.type_specification
                )
            )
            .scalar_one()
            .id,
        )
    database.session.add_all(bikes.values())
    database.session.commit()

    data = get_rides_in_timeframe(timeframe="All", ride_type="Any")
    rides = {}
    overviews = {}
    added_track_ids = []
    added_tracks = {}
    old_new_track_id_map = {}
    for rcrd in data.sort_values(by="id_ride", ascending=True).to_dict("records"):
        # print(rcrd)
        # if len(rides) > 10:
        #     break
        this_ride = Ride(
            ride_date=rcrd["date"],
            start_time=rcrd["start_time"],
            ride_duration=None if pd.isna(rcrd["ride_time"]) else rcrd["ride_time"],
            total_duration=rcrd["total_time"],
            distance=rcrd["distance"],
            id_bike=bikes[rcrd["bike"]].id,
            id_terrain_type=database.session.execute(
                database.select(TerrainType).filter_by(text=rcrd["ride_type"])
            )
            .scalar_one()
            .id,
        )
        rides[rcrd["id_ride"]] = this_ride

        this_overview = TrackOverview(
            # id_track=-1,
            id_segment=None,
            moving_time_seconds=rcrd["moving_time_seconds"],
            total_time_seconds=rcrd["total_time_seconds"],
            moving_distance=rcrd["moving_distance"],
            total_distance=rcrd["total_distance"],
            max_velocity=rcrd["max_velocity"],
            avg_velocity=rcrd["avg_velocity"],
            max_elevation=rcrd["max_elevation"],
            min_elevation=rcrd["min_elevation"],
            uphill_elevation=rcrd["uphill_elevation"],
            downhill_elevation=rcrd["downhill_elevation"],
            moving_distance_km=rcrd["moving_distance_km"],
            total_distance_km=rcrd["total_distance_km"],
            max_velocity_kmh=rcrd["max_velocity_kmh"],
            avg_velocity_kmh=rcrd["avg_velocity_kmh"],
            bounds_min_lat=rcrd["bounds_min_lat"],
            bounds_max_lat=rcrd["bounds_max_lat"],
            bounds_min_lng=rcrd["bounds_min_lng"],
            bounds_max_lng=rcrd["bounds_max_lng"],
        )

        tracks_added = 0
        overview_added = False

        if ride_has_track(rcrd["id_ride"], "tracks"):
            track_ids = ride_track_ids(rcrd["id_ride"], "tracks")
            if track_ids is None:
                raise RuntimeError
            for id_track in track_ids:
                data = get_track_data(id_track, "tracks")
                data_dict = dict(
                    content=data,
                    added=datetime.combine(
                        rcrd["date"],
                        rcrd["start_time"],
                    )
                    + timedelta(seconds=360 * tracks_added),
                )
                # if id_track == rcrd["id_track"] and not overview_added:
                #     data_dict["overviews"] = [this_overview]

                this_ride.tracks.append(DatabaseTrack(**data_dict))
                tracks_added += 1

        if ride_has_track(rcrd["id_ride"], "tracks_enhanced_v1"):
            track_ids = ride_track_ids(rcrd["id_ride"], "tracks_enhanced_v1")
            if track_ids is None:
                raise RuntimeError
            for id_track in track_ids:
                data = get_track_data(id_track, "tracks_enhanced_v1")
                data_dict = dict(
                    content=data,
                    added=datetime.combine(
                        rcrd["date"],
                        rcrd["start_time"],
                    )
                    + timedelta(seconds=360 * tracks_added),
                    is_enhanced=True,
                )
                if id_track == rcrd["id_track"]:
                    data_dict["overviews"] = [this_overview]
                    overview_added = True
                this_ride.tracks.append(DatabaseTrack(**data_dict))
                added_track_ids.append(id_track)
                tracks_added += 1
            added_tracks[rcrd["id_track"]] = this_ride
        database.session.add(this_ride)
        database.session.commit()
        overviews[rcrd["id_track"]] = TrackOverview(
            id_track=-1,
            id_segment=None,
            moving_time_seconds=rcrd["moving_time_seconds"],
            total_time_seconds=rcrd["total_time_seconds"],
            moving_distance=rcrd["moving_distance"],
            total_distance=rcrd["total_distance"],
            max_velocity=rcrd["max_velocity"],
            avg_velocity=rcrd["avg_velocity"],
            max_elevation=rcrd["max_elevation"],
            min_elevation=rcrd["min_elevation"],
            uphill_elevation=rcrd["uphill_elevation"],
            downhill_elevation=rcrd["downhill_elevation"],
            moving_distance_km=rcrd["moving_distance_km"],
            total_distance_km=rcrd["total_distance_km"],
            max_velocity_kmh=rcrd["max_velocity_kmh"],
            avg_velocity_kmh=rcrd["avg_velocity_kmh"],
            bounds_min_lat=rcrd["bounds_min_lat"],
            bounds_max_lat=rcrd["bounds_max_lat"],
            bounds_min_lng=rcrd["bounds_min_lng"],
            bounds_max_lng=rcrd["bounds_max_lng"],
        )

    # database.session.add_all(rides)

    # for id_track, overview in overviews.items():
    #     if np.isnan(id_track):
    #         continue
    #     print(added_tracks[id_track].id)
    #     overview.id_track = added_tracks[id_track].id
    #     database.session.add(overview)
    #     # database.session.add_all([o for i, o in overviews.items() if i in added_track_ids])
    #     database.session.commit()

    events = []
    for event in get_events(None, None, None):
        print(event)
        this_event = DatabaseEvent(
            event_date=event["date"],
            id_event_type=database.session.execute(
                database.select(EventType).filter_by(text=event["event_type"])
            )
            .scalar_one()
            .id,
            short_description=event["short_description"],
            description=event["description"],
            id_severity=None if event["severity"] is None else event["severity"] + 1,
            latitude=event["latitude"],
            longitude=event["longitude"],
            id_bike=bikes[event["bike"]].id,
        )
        events.append(this_event)
        if event["id_ride"] is not None and event["id_ride"] in rides.keys():
            rides[event["id_ride"]].events.append(this_event)
        database.session.add(this_event)
        database.session.commit()

    for id_ride, note_text in get_all_notes():
        # print(id_ride, note_text)
        this_note = RideNote(text=note_text)
        if id_ride in rides.keys():
            rides[id_ride].notes.append(this_note)
        database.session.add(this_note)
        database.session.commit()

    for segment in get_all_segments(
        {
            int(key): value
            for key, value in current_app.config.mappings.difficulty.to_dict().items()
        }
    ):
        # print(segment)
        database.session.add(
            DatabaseSegment(
                name=segment.name,
                description=segment.description,
                id_segment_type=database.session.execute(
                    database.select(SegmentType).filter_by(text=segment.type)
                )
                .scalar_one()
                .id,
                id_difficulty=database.session.execute(
                    database.select(Difficulty).filter_by(text=segment.difficulty)
                )
                .scalar_one()
                .id,
                distance=segment.distance,
                min_elevation=segment.min_elevation,
                max_elevation=segment.max_elevation,
                uphill_elevation=segment.uphill_elevation,
                downhill_elevation=segment.downhill_elevation,
                bounds_min_lat=segment.bounds.min_latitude,
                bounds_max_lat=segment.bounds.max_latitude,
                bounds_min_lng=segment.bounds.min_longitude,
                bounds_max_lng=segment.bounds.max_longitude,
                visited=segment.visited,
                gpx=segment.track.get_xml().encode(),
            )
        )
        database.session.commit()


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
            for key in data.keys()
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
                data[key].append(None)
            else:
                data[key].append(getattr(overview, key))

    data_df = pd.DataFrame(data)
    if not data_df.empty:
        data_df["year"] = data_df.apply(lambda r: r.date.year, axis=1)
        data_df["month"] = data_df.apply(lambda r: month_labels[r.date.month], axis=1)

    return data_df


def summarize_rides_in_year(rides: list[Ride]) -> list[tuple[str, str]]:
    # FIXME
    data = convert_rides_to_df(rides)
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
            "tot_time": str(data.ride_time.sum()).split(".")[0],
            "num_rides": str(len(data)),
            "avg_distance": str(round(data.distance.mean(), 2)),
            "avg_ride_duration": str(data.ride_time.mean())
            .split(".")[0]
            .replace("0 days ", ""),
        }

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

    return summary_data


def summarize_rides_in_month(
    rides_curr_month: list[Ride], rides_prev_month: list[Ride]
) -> list[tuple[str, str]]:
    curr_month_data = convert_rides_to_df(rides_curr_month)
    last_month_data = convert_rides_to_df(rides_prev_month)

    curr_month_distance = curr_month_data.distance.sum()
    last_month_distance = last_month_data.distance.sum()

    curr_month_ride_time = curr_month_data.ride_time.sum()
    last_month_ride_time = last_month_data.ride_time.sum()
    if curr_month_ride_time == 0:
        curr_month_ride_time = pd.Timedelta(seconds=0)
    if last_month_ride_time == 0:
        last_month_ride_time = pd.Timedelta(seconds=0)
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
                curr_month_ride_time - last_month_ride_time,
                pd.Timedelta(minutes=15),
            ),
        ),
        (
            "Rides",
            curr_month_count,
            compare_values(curr_month_count - last_month_count, 1),
        ),
    ]

    return summary_month


def convert_database_goals(data: list[DatabaseGoal]) -> list[Goal]:
    from cycle_analytics.model.goal import MonthlyGoal, YearlyGoal

    goals: list[Goal] = []

    for db_goal in data:
        if db_goal.month is None:
            goals.append(YearlyGoal(**asdict(db_goal)))
        else:
            if db_goal.month == 0:
                for i in range(1, 13):
                    goal_dict = asdict(db_goal)
                    goal_dict["month"] = i
                    goals.append(MonthlyGoal(**goal_dict))
            else:
                goals.append(MonthlyGoal(**asdict(db_goal)))

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

    return TrackOverview(**data)


# TEMP: Update this with track_analyzer >=1.0
# TODO: Should check if multipel segments. If yes, get track_overview and insert with
# TODO: id_segment=None and then add segment overviews. If not, just inster with
# TODO: id_segment = None
def initialize_overviews(
    track: Track,
    id_track: None | int = None,
) -> list[TrackOverview]:
    bounds = track.track.segments[0].get_bounds()
    return [
        track_to_db_overview(
            track.get_segment_overview(0),
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
