# import importlib.resources
from datetime import date, datetime, time, timedelta
from typing import Any

import numpy as np
from flask_sqlalchemy import SQLAlchemy
from geo_track_analyzer import PyTrack, Track

from cycle_analytics.database.converter import initialize_overviews
from cycle_analytics.database.model import (
    Bike,
    DatabaseEvent,
    DatabaseGoal,
    DatabaseSegment,
    DatabaseTrack,
    Ride,
    RideNote,
    SegmentType,
)

# from tests import resources


def create_test_data(database: SQLAlchemy, data: dict[str, Any]) -> None:
    rng = np.random.default_rng()
    this_year = datetime.now().year
    this_month = datetime.now().month
    last_year = this_year - 1

    fr_track_top_segment: Track = data["fr_track_top_segment"]
    fr_track_sub_segment: Track = data["fr_track_sub_segment"]
    fr_track: Track = data["fr_track"]
    # Generate some bikes
    bike_1 = Bike(
        name="Bike 1",
        brand="Brand 1",
        model="Model 1",
        id_material=1,
        id_specification=1,
        id_terraintype=1,
        commission_date=datetime.now().date(),
    )
    bike_2 = Bike(
        name="Bike 2",
        brand="Brand 1",
        model="Model 2",
        id_material=2,
        id_specification=2,
        id_terraintype=2,
        commission_date=datetime.now().date(),
    )

    database.session.add_all([bike_1, bike_2])
    database.session.commit()

    # Generate some rides
    ride_last_year_1 = Ride(
        ride_date=date(last_year, 11, 10),
        start_time=time(12, 00, 00),
        ride_duration=None,
        total_duration=timedelta(seconds=(60 * 60)),
        distance=12,
        id_terrain_type=1,
        id_bike=bike_1.id,
    )
    ride_last_year_2 = Ride(
        ride_date=date(last_year, 12, 10),
        start_time=time(12, 00, 00),
        ride_duration=None,
        total_duration=timedelta(seconds=(60 * 60)),
        distance=42,
        id_terrain_type=1,
        id_bike=bike_1.id,
    )

    database.session.add_all([ride_last_year_1, ride_last_year_2])
    database.session.commit()

    ride_0 = Ride(
        ride_date=date(this_year, this_month, 1),
        start_time=time(13, 00, 00),
        ride_duration=timedelta(seconds=60 * 60 * 3),
        total_duration=timedelta(seconds=(60 * 60 * 3) + 60),
        distance=42.42,
        id_terrain_type=2,
        id_bike=bike_2.id,
    )

    ride_1 = Ride(
        ride_date=date(this_year, 8, 1),
        start_time=time(12, 00, 00),
        ride_duration=timedelta(seconds=60 * 20),
        total_duration=timedelta(seconds=(60 * 20) + 60),
        distance=5.7,
        id_terrain_type=2,
        id_bike=bike_2.id,
    )

    ride_1.tracks.extend(
        [
            DatabaseTrack(
                content=fr_track_sub_segment.get_xml().encode(),
                added=datetime(this_year, 8, 1, 18),
                is_enhanced=False,
            ),
            DatabaseTrack(
                content=fr_track_sub_segment.get_xml().encode(),
                added=datetime(this_year, 8, 1, 18, 10),
                is_enhanced=True,
                overviews=initialize_overviews(fr_track_sub_segment),
            ),
        ]
    )

    ride_1.notes.append(RideNote(text="Some note"))

    ride_1.events.extend(
        [
            DatabaseEvent(
                event_date=date(this_year, 8, 1),
                id_event_type=1,
                short_description="Some event for ride 1",
                id_bike=bike_2.id,
            ),
            DatabaseEvent(
                event_date=date(this_year, 8, 1),
                id_event_type=2,
                short_description="Some located event for ride 1",
                latitude=47.932704,
                longitude=7.875811,
                id_bike=bike_2.id,
                id_severity=4,
            ),
            DatabaseEvent(
                event_date=date(this_year, 8, 1),
                id_event_type=2,
                short_description="Some located event for ride 1",
                description="Lorem ipsum dolor sit amet, consetetur sadipscing elitr, "
                "sed diam nonumy eirmod tempor invidunt.",
                latitude=47.931671,
                longitude=7.88191,
                id_bike=bike_2.id,
                id_severity=2,
            ),
        ]
    )

    ride_2 = Ride(
        ride_date=date(this_year, 8, 8),
        start_time=time(12, 00, 00),
        ride_duration=None,
        total_duration=timedelta(seconds=(60 * 60)),
        distance=19.7,
        id_terrain_type=2,
        id_bike=bike_2.id,
    )

    ride_2.tracks.extend(
        [
            DatabaseTrack(
                content=fr_track.get_xml().encode(),
                added=datetime(this_year, 8, 8, 18),
                is_enhanced=False,
            ),
        ]
    )

    ride_3 = Ride(
        ride_date=date(this_year, 8, 2),
        start_time=time(14, 00, 00),
        ride_duration=None,
        total_duration=timedelta(seconds=(60 * 10)),
        distance=3.33,
        id_terrain_type=2,
        id_bike=bike_2.id,
    )

    points = []
    times = []

    for i in range(0, 60, 2):
        points.extend(
            [
                (47.99609 + i * 0.0001, 7.849401 + i * 0.0001),
                (47.99609 + (i + 1) * 0.0001, 7.849401 + (i + 2) * 0.0001),
            ]
        )
        times.extend(
            [
                datetime(this_year, 8, 2, 14, 0, 00) + (i * timedelta(seconds=30)),
                datetime(this_year, 8, 2, 14, 0, 00)
                + ((i + 1) * timedelta(seconds=30)),
            ]
        )

    track_with_extensions = PyTrack(
        points=points,
        times=times,
        elevations=rng.integers(150, 200, size=len(points)).tolist(),
        heartrate=rng.integers(100, 170, size=len(points)).tolist(),
        cadence=rng.integers(40, 80, size=len(points)).tolist(),
        power=rng.integers(200, 350, size=len(points)).tolist(),
    )

    ride_3.tracks.extend(
        [
            DatabaseTrack(
                content=track_with_extensions.get_xml().encode(),
                added=datetime(this_year, 8, 2, 18),
                is_enhanced=True,
            ),
        ]
    )

    database.session.add_all([ride_0, ride_1, ride_2, ride_3])
    database.session.commit()

    # Generate some Events
    event_1 = DatabaseEvent(
        event_date=date(last_year, 11, 1),
        id_event_type=1,
        short_description="Short desciption of event 1",
    )
    event_2 = DatabaseEvent(
        event_date=date(last_year, 12, 20),
        id_event_type=1,
        short_description="Short desciption of event 2",
    )
    event_3 = DatabaseEvent(
        event_date=date(this_year, 1, 1),
        id_event_type=1,
        short_description="Short desciption of event 3",
    )
    event_4 = DatabaseEvent(
        event_date=date(this_year, 1, 1),
        id_event_type=2,
        short_description="Short desciption of event 4",
        description="Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. At vero eos et accusam et justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimata sanctus est Lorem ipsum dolor sit amet.",  # noqa: E501
        id_severity=4,
        id_bike=bike_1.id,
        latitude=47.972,
        longitude=7.860162,
    )
    database.session.add_all([event_1, event_2, event_3, event_4])
    database.session.commit()

    # Generate some segments
    sample_segments = []
    segment_types: list[SegmentType] = SegmentType.query.all()
    for i, st in enumerate(segment_types):
        track = PyTrack(
            points=[
                (47.99609 + (i * 0.00001), 7.849401 + (i * 0.00001)),
                (47.99079 + (i * 0.00001), 7.829867 + (i * 0.00001)),
            ],
            elevations=None,
            times=None,
        )
        bounds = track.track.segments[0].get_bounds()

        sample_segments.append(
            DatabaseSegment(
                name=f"Sample Segment of type {st.text}",
                id_segment_type=st.id,
                id_difficulty=1,
                distance=4.24242 * (i + 1),
                bounds_min_lat=bounds.min_latitude,
                bounds_max_lat=bounds.max_latitude,
                bounds_min_lng=bounds.min_longitude,
                bounds_max_lng=bounds.max_longitude,
                gpx=track.get_xml().encode(),
            )
        )

    bounds = fr_track_top_segment.track.segments[0].get_bounds()
    overview = fr_track_top_segment.get_segment_overview(0)

    fr_top_db_segment = DatabaseSegment(
        name="Top part of FR segment",
        description="Some longer description of the FR track",
        id_segment_type=next(iter([s for s in segment_types if s.text == "Road"])).id,
        id_difficulty=1,
        distance=overview.total_distance_km,
        min_elevation=overview.min_elevation,
        max_elevation=overview.max_elevation,
        uphill_elevation=overview.uphill_elevation,
        downhill_elevation=overview.downhill_elevation,
        bounds_min_lat=bounds.min_latitude,
        bounds_max_lat=bounds.max_latitude,
        bounds_min_lng=bounds.min_longitude,
        bounds_max_lng=bounds.max_longitude,
        gpx=fr_track_top_segment.get_xml().encode(),
    )

    sample_segments.append(fr_top_db_segment)
    database.session.add_all(sample_segments)
    database.session.commit()
    # Generate some goals
    database.session.add_all(
        [
            DatabaseGoal(
                year=this_year,
                month=None,
                name="Yearly Goal",
                goal_type="total_distance",
                threshold=500,
                is_upper_bound=True,
            ),
            DatabaseGoal(
                year=this_year,
                month=0,
                name="Monthly Goal (Every month)",
                goal_type="count",
                threshold=5,
                is_upper_bound=True,
            ),
            DatabaseGoal(
                year=this_year,
                month=this_month,
                name="Monthly Goal (Specific goal, avg. distance)",
                goal_type="avg_distance",
                threshold=10,
                is_upper_bound=True,
            ),
            DatabaseGoal(
                year=this_year,
                month=this_month,
                name="Monthly Goal (Specific goal, max. distance)",
                goal_type="max_distance",
                threshold=25,
                is_upper_bound=True,
            ),
        ]
    )
    database.session.commit()
