from datetime import datetime, timedelta

import pandas as pd
from flask import current_app
from flask_sqlalchemy import SQLAlchemy

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

from .model import (
    Bike,
    DatabaseEvent,
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


def convert_data(database: SQLAlchemy):
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
