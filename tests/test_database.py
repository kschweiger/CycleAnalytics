from datetime import date, datetime, time, timedelta

import pytest
from flask import Flask, current_app
from geo_track_analyzer import PyTrack, Track

from cycle_analytics.database.converter import initialize_overviews
from cycle_analytics.database.model import DatabaseTrack, Ride
from cycle_analytics.database.model import db as orm_db
from cycle_analytics.database.retriever import get_segments_for_map_in_bounds


def test_get_segments_for_map_in_bounds_nothing(app: Flask) -> None:
    with app.app_context():
        config = current_app.config
        assert (
            len(
                get_segments_for_map_in_bounds(
                    [], 1, 1, 0, 0, config.mappings.segment_types, "some/route/"
                )
            )
            == 0
        )


def test_get_segments_for_map_in_bounds_all(app: Flask) -> None:
    with app.app_context():
        config = current_app.config
        segments_0 = get_segments_for_map_in_bounds(
            [], 48, 8, 47, 7, config.mappings.segment_types, "some/route/"
        )
        assert len(segments_0) > 0

        segments_1 = get_segments_for_map_in_bounds(
            [s.segment_id for s in segments_0],
            48,
            8,
            47,
            7,
            config.mappings.segment_types,
            "some/route/",
        )

        assert len(segments_1) == 0


def test_initialize_overviews_single_segment() -> None:
    this_year = datetime.now().year
    this_month = datetime.now().month
    track = PyTrack(
        points=[(1, 1), (1.001, 1.001), (1.002, 1.002)],
        elevations=[100, 120, 140],
        times=[
            datetime(this_year, this_month, 1, 12),
            datetime(this_year, this_month, 1, 12, 1),
            datetime(this_year, this_month, 1, 12, 2),
        ],
    )

    overviews = initialize_overviews(track, 42)

    assert len(overviews) == 1
    assert overviews[0].id_track == 42
    assert overviews[0].id_segment is None


@pytest.fixture(scope="session")
def test_track_with_segments() -> Track:
    this_year = datetime.now().year
    this_month = datetime.now().month
    track = PyTrack(
        points=[(1, 1), (1.001, 1.001), (1.002, 1.002)],
        elevations=[100.0, 120.0, 140.0],
        times=[
            datetime(this_year, this_month, 1, 12),
            datetime(this_year, this_month, 1, 12, 1),
            datetime(this_year, this_month, 1, 12, 2),
        ],
    )

    track.add_segmeent(
        points=[(1.003, 1.003), (1.004, 1.004), (1.005, 1.005)],
        elevations=[160.0, 180.0, 200.0],
        times=[
            datetime(this_year, this_month, 1, 12, 3),
            datetime(this_year, this_month, 1, 12, 4),
            datetime(this_year, this_month, 1, 12, 5),
        ],
    )

    return track


@pytest.mark.dependency()
def test_initialize_overviews_two_segments(test_track_with_segments: Track) -> None:
    overviews = initialize_overviews(test_track_with_segments, 42)

    assert len(overviews) == 3
    assert overviews[0].id_track == 42
    assert overviews[0].id_segment is None
    assert overviews[1].id_track == 42
    assert overviews[1].id_segment == 0
    assert overviews[2].id_track == 42
    assert overviews[2].id_segment == 1


@pytest.mark.dependency(depends=["test_initialize_overviews_two_segments"])
def test_insert_multi_segment_overview(
    app: Flask, test_track_with_segments: Track
) -> None:
    this_year = datetime.now().year
    this_month = datetime.now().month
    test_insert_ride = Ride(
        ride_date=date(this_year, this_month, 1),
        start_time=time(12, 0),
        total_duration=timedelta(6 * 60),
        distance=4.4,
        id_bike=1,
        id_terrain_type=1,
    )

    test_insert_ride.tracks.append(
        DatabaseTrack(
            content=test_track_with_segments.get_xml().encode(),
            added=datetime(this_year, this_month, 1, 20),
            is_enhanced=True,
            overviews=initialize_overviews(test_track_with_segments),
        )
    )

    with app.app_context():
        orm_db.session.add(test_insert_ride)
        orm_db.session.commit()
