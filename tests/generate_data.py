# import importlib.resources
from datetime import date, datetime, time, timedelta
from typing import Any

import numpy as np
from flask_sqlalchemy import SQLAlchemy
from geo_track_analyzer import PyTrack, Track
from sqlalchemy import select

from cycle_analytics.database.converter import initialize_overviews
from cycle_analytics.database.model import (
    Bike,
    DatabaseEvent,
    DatabaseGoal,
    DatabaseLocation,
    DatabaseSegment,
    DatabaseTrack,
    DatabaseZoneInterval,
    Difficulty,
    EventType,
    Material,
    Ride,
    RideNote,
    SegmentType,
    Severity,
    TerrainType,
    TrackLocationAssociation,
    TypeSpecification,
)

# from tests import resources


def create_test_data(database: SQLAlchemy, data: dict[str, Any]) -> None:
    rng = np.random.default_rng()
    this_year = datetime.now().year
    this_month = datetime.now().month
    last_year = this_year - 1

    materials = database.session.scalars(select(Material)).all()
    terrain_types = database.session.scalars(select(TerrainType)).all()
    specifications = database.session.scalars(select(TypeSpecification)).all()
    event_types = database.session.scalars(select(EventType)).all()
    severities = database.session.scalars(select(Severity)).all()
    difficulties = database.session.scalars(select(Difficulty)).all()

    fr_track_top_segment: Track = data["fr_track_top_segment"]
    fr_track_sub_segment: Track = data["fr_track_sub_segment"]
    fr_track: Track = data["fr_track"]
    # Generate some bikes
    bike_1 = Bike(
        name="Bike 1",
        brand="Brand 1",
        model="Model 1",
        material=materials[0],
        specification=specifications[0],
        terrain_type=terrain_types[0],
        commission_date=datetime.now().date(),
    )
    bike_2 = Bike(
        name="Bike 2",
        brand="Brand 1",
        model="Model 2",
        material=materials[1],
        specification=specifications[1],
        terrain_type=terrain_types[1],
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
        terrain_type=terrain_types[0],
        bike=bike_1,
    )
    ride_last_year_2 = Ride(
        ride_date=date(last_year, 12, 10),
        start_time=time(12, 00, 00),
        ride_duration=None,
        total_duration=timedelta(seconds=(60 * 60)),
        distance=42,
        terrain_type=terrain_types[0],
        bike=bike_1,
    )

    database.session.add_all([ride_last_year_1, ride_last_year_2])
    database.session.commit()

    ride_0 = Ride(
        ride_date=date(this_year, this_month, 1),
        start_time=time(13, 00, 00),
        ride_duration=timedelta(seconds=60 * 60 * 3),
        total_duration=timedelta(seconds=(60 * 60 * 3) + 60),
        distance=42.42,
        terrain_type=terrain_types[1],
        bike=bike_2,
    )

    ride_1 = Ride(
        ride_date=date(this_year, 8, 1),
        start_time=time(12, 00, 00),
        ride_duration=timedelta(seconds=60 * 20),
        total_duration=timedelta(seconds=(60 * 20) + 60),
        distance=5.7,
        terrain_type=terrain_types[1],
        bike=bike_2,
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
                event_type=event_types[0],
                short_description="Some event for ride 1",
                bike=bike_2,
            ),
            DatabaseEvent(
                event_date=date(this_year, 8, 1),
                event_type=event_types[1],
                short_description="Some located event for ride 1",
                latitude=47.932704,
                longitude=7.875811,
                bike=bike_2,
                severity=severities[3],
            ),
            DatabaseEvent(
                event_date=date(this_year, 8, 1),
                event_type=event_types[1],
                short_description="Some located event for ride 1",
                description="Lorem ipsum dolor sit amet, consetetur sadipscing elitr, "
                "sed diam nonumy eirmod tempor invidunt.",
                latitude=47.931671,
                longitude=7.88191,
                bike=bike_2,
                severity=severities[1],
            ),
        ]
    )

    ride_2 = Ride(
        ride_date=date(this_year, 8, 8),
        start_time=time(12, 00, 00),
        ride_duration=None,
        total_duration=timedelta(seconds=(60 * 60)),
        distance=19.7,
        terrain_type=terrain_types[1],
        bike=bike_2,
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
        terrain_type=terrain_types[1],
        bike=bike_2,
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
    elevations = rng.integers(150, 200, size=len(points)).tolist()
    heartrate = rng.integers(100, 170, size=len(points)).tolist()
    cadence = rng.integers(40, 80, size=len(points)).tolist()
    power = rng.integers(200, 350, size=len(points)).tolist()

    track_with_extensions = PyTrack(
        points=points[0:30],
        times=times[0:30],
        elevations=elevations[0:30],
        heartrate=heartrate[0:30],
        cadence=cadence[0:30],
        power=power[0:30],
    )
    track_with_extensions.add_segmeent(
        points=points[30:],
        times=times[30:],
        elevations=elevations[30:],
        heartrate=heartrate[30:],
        cadence=cadence[30:],
        power=power[30:],
    )

    extension_db_track = DatabaseTrack(
        content=track_with_extensions.get_xml().encode(),
        added=datetime(this_year, 8, 2, 18),
        is_enhanced=True,
        overviews=initialize_overviews(track_with_extensions),
    )

    ride_3.tracks.extend([extension_db_track])

    database.session.add_all([ride_0, ride_1, ride_2, ride_3])
    database.session.commit()

    # Generate some Events
    event_1 = DatabaseEvent(
        event_date=date(last_year, 11, 1),
        event_type=event_types[0],
        short_description="Short desciption of event 1",
    )
    event_2 = DatabaseEvent(
        event_date=date(last_year, 12, 20),
        event_type=event_types[0],
        short_description="Short desciption of event 2",
    )
    event_3 = DatabaseEvent(
        event_date=date(this_year, 1, 1),
        event_type=event_types[0],
        short_description="Short desciption of event 3",
    )
    event_4 = DatabaseEvent(
        event_date=date(this_year, 1, 1),
        event_type=event_types[1],
        short_description="Short desciption of event 4",
        description="Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. At vero eos et accusam et justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimata sanctus est Lorem ipsum dolor sit amet.",  # noqa: E501
        severity=severities[3],
        bike=bike_1,
        latitude=47.972,
        longitude=7.860162,
    )
    database.session.add_all([event_1, event_2, event_3, event_4])
    database.session.commit()

    # Generate some segments
    sample_segments = []
    segment_types = database.session.scalars(select(SegmentType)).all()
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
                segment_type=st,
                difficulty=difficulties[0],
                distance=4.24242 * (i + 1),
                bounds_min_lat=bounds.min_latitude,  # type: ignore
                bounds_max_lat=bounds.max_latitude,  # type: ignore
                bounds_min_lng=bounds.min_longitude,  # type: ignore
                bounds_max_lng=bounds.max_longitude,  # type: ignore
                gpx=track.get_xml().encode(),
            )
        )

    bounds = fr_track_top_segment.track.segments[0].get_bounds()
    overview = fr_track_top_segment.get_segment_overview(0)

    fr_top_db_segment = DatabaseSegment(
        name="Top part of FR segment",
        description="Some longer description of the FR track",
        segment_type=next(iter([s for s in segment_types if s.text == "Road"])),
        difficulty=difficulties[0],
        distance=overview.total_distance_km,
        min_elevation=overview.min_elevation,
        max_elevation=overview.max_elevation,
        uphill_elevation=overview.uphill_elevation,
        downhill_elevation=overview.downhill_elevation,
        bounds_min_lat=bounds.min_latitude,  # type: ignore
        bounds_max_lat=bounds.max_latitude,  # type: ignore
        bounds_min_lng=bounds.min_longitude,  # type: ignore
        bounds_max_lng=bounds.max_longitude,  # type: ignore
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
                goal_type="ride",
                aggregation_type="total_distance",
                threshold=500,
                is_upper_bound=True,
            ),
            DatabaseGoal(
                year=this_year,
                month=0,
                name="Monthly Goal (Every month)",
                goal_type="ride",
                aggregation_type="count",
                threshold=5,
                is_upper_bound=True,
            ),
            DatabaseGoal(
                year=this_year,
                month=this_month,
                name="Monthly Goal (Specific goal, avg. distance)",
                goal_type="ride",
                aggregation_type="avg_distance",
                threshold=10,
                is_upper_bound=True,
            ),
            DatabaseGoal(
                year=this_year,
                month=this_month,
                name="Monthly Goal (Specific goal, max. distance)",
                goal_type="ride",
                aggregation_type="max_distance",
                threshold=25,
                is_upper_bound=True,
            ),
            DatabaseGoal(
                year=this_year,
                month=this_month,
                name="Monthly Goal (duration)",
                goal_type="ride",
                aggregation_type="duration",
                threshold=60 * 60,
                is_upper_bound=True,
            ),
            DatabaseGoal(
                year=this_year,
                month=this_month,
                name="Manual goal 1",
                goal_type="manual",
                aggregation_type="count",
                threshold=5,
                is_upper_bound=True,
                value=2,
            ),
            DatabaseGoal(
                year=this_year,
                month=this_month,
                name="Manual goal 2",
                goal_type="manual",
                aggregation_type="count",
                threshold=5,
                is_upper_bound=True,
            ),
            DatabaseGoal(
                year=this_year,
                month=this_month,
                name="Manual duration goal",
                goal_type="manual",
                aggregation_type="duration",
                threshold=60,
                is_upper_bound=True,
            ),
        ]
    )
    database.session.commit()

    database.session.add_all(
        [
            DatabaseLocation(
                latitude=47.940564453431236, longitude=7.867881953716279, name="Loc 1"
            ),
            DatabaseLocation(
                latitude=47.938265883037424, longitude=7.866286039352418, name="Loc 2"
            ),
            DatabaseLocation(latitude=40, longitude=9, name="Location 1"),
            DatabaseLocation(
                latitude=41,
                longitude=9.5,
                name="Location 2",
                description="Description for location 2",
            ),
        ]
    )
    database.session.commit()
    location_for_goal = DatabaseLocation(
        latitude=47.99609 + 0.0002,
        longitude=7.849401 + 0.0002,
        name="Goal Location",
    )

    database.session.add(location_for_goal)
    database.session.commit()

    database.session.add(
        DatabaseGoal(
            year=this_year,
            month=None,
            name="Default location goal",
            goal_type="location",
            aggregation_type="count",
            threshold=1,
            is_upper_bound=True,
            constraints={"id_location": location_for_goal.id},
        ),
    )
    database.session.commit()

    database.session.add(
        TrackLocationAssociation(
            location_id=location_for_goal.id,
            track_id=extension_db_track.id,
            distance=10,
        )
    )
    database.session.commit()

    database.session.add_all(
        [
            DatabaseZoneInterval(
                id=0,
                metric="heartrate",
                interval_start=None,
                interval_end=100,
                name="Easy",
                color="#FF0000",
            ),
            DatabaseZoneInterval(
                id=1,
                metric="heartrate",
                interval_start=100,
                interval_end=150,
                name="Moderate",
                color="#0000FF",
            ),
            DatabaseZoneInterval(
                id=2,
                metric="heartrate",
                interval_start=150,
                interval_end=None,
                name="Hard",
                color="#00FF00",
            ),
            DatabaseZoneInterval(
                id=0,
                metric="power",
                interval_start=None,
                interval_end=150,
                name=None,
                color=None,
            ),
            DatabaseZoneInterval(
                id=1,
                metric="power",
                interval_start=150,
                interval_end=None,
                name=None,
                color=None,
            ),
        ]
    )
    database.session.commit()
