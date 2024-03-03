import hashlib
import logging
from datetime import datetime

from flask import current_app, flash
from geo_track_analyzer.enhancer import get_enhancer
from geo_track_analyzer.exceptions import (
    APIHealthCheckFailedError,
    APIResponseError,
)
from geo_track_analyzer.model import Position2D
from geo_track_analyzer.track import Track
from geo_track_analyzer.utils.base import (
    get_latitude_at_distance,
    get_longitude_at_distance,
)

from cycle_analytics.database.converter import initialize_overviews
from cycle_analytics.database.model import DatabaseLocation, DatabaseTrack
from cycle_analytics.utils.base import unwrap
from cycle_analytics.utils.debug import log_timing

numeric = int | float
logger = logging.getLogger(__name__)


def init_db_track_and_enhance(track: Track, is_enhanced: bool) -> list[DatabaseTrack]:
    tracks = []
    tracks.append(
        DatabaseTrack(
            content=track.get_xml().encode(),
            added=datetime.now(),
            is_enhanced=is_enhanced,
            overviews=initialize_overviews(track, None),
        )
    )
    flash("Track added", "alert-success")
    if not is_enhanced:
        enhanced_db_track = get_enhanced_db_track(track)
        if enhanced_db_track:
            tracks.append(enhanced_db_track)

    return tracks


def get_enhanced_db_track(track: Track) -> None | DatabaseTrack:
    try:
        enhancer = get_enhancer(current_app.config.external.track_enhancer.name)(
            url=current_app.config.external.track_enhancer.url,
            **current_app.config.external.track_enhancer.kwargs.to_dict(),
        )  # type: ignore
    except APIHealthCheckFailedError:
        logger.warning("Enhancer not available. Skipping elevation profile")
        flash("Track could not be enhanced - API not available", "alert-danger")
        return None

    try:
        enhancer.enhance_track(track.track, True)
    except APIResponseError:
        flash("Could not enhance track with elevation", "alert-danger")
        logger.error("Could not enhance track with elevation")
        return None

    flash("Enhanced track added", "alert-success")
    return DatabaseTrack(
        content=track.get_xml().encode(),
        added=datetime.now(),
        is_enhanced=True,
        overviews=initialize_overviews(track, None),
    )


def check_location_in_track(
    track: Track, locations: list[DatabaseLocation], max_distance: float
) -> list[bool]:
    bounds = unwrap(track.track.get_bounds())
    bounds_min_lat = unwrap(bounds.min_latitude)
    bounds_max_lat = unwrap(bounds.max_latitude)
    bounds_min_lng = unwrap(bounds.min_longitude)
    bounds_max_lng = unwrap(bounds.max_longitude)

    # +---------+ < max_lat
    # |         |
    # +---------+ < min_lat
    # ^         ^
    # min_long  max_long
    max_lng_ext = get_longitude_at_distance(
        Position2D(latitude=bounds_max_lat, longitude=bounds_max_lng),
        max_distance,
        True,
    )
    min_lng_ext = get_longitude_at_distance(
        Position2D(latitude=bounds_max_lat, longitude=bounds_min_lng),
        max_distance,
        False,
    )

    max_lat_ext = get_latitude_at_distance(
        Position2D(latitude=bounds_max_lat, longitude=bounds_max_lng),
        max_distance,
        True,
    )
    min_lat_ext = get_latitude_at_distance(
        Position2D(latitude=bounds_min_lat, longitude=bounds_max_lng),
        max_distance,
        False,
    )

    match = []
    for location in locations:
        if (
            location.longitude > max_lng_ext
            or location.longitude < min_lng_ext
            or location.latitude > max_lat_ext
            or location.latitude < min_lat_ext
        ):
            match.append(False)
            continue

        closest_point = track.get_closest_point(
            n_segment=None, longitude=location.longitude, latitude=location.latitude
        )

        match.append(closest_point.distance <= max_distance)

    return match


# TEMP: Something like this should be part of
# TEMP: the Track object
@log_timing
def get_identifier(track: Track) -> str:
    m = hashlib.sha256()
    bounds = track.track.get_bounds()
    time_bounds = track.track.get_time_bounds()
    center = track.track.get_center()
    if center:
        m.update(str(center.latitude).encode())
        m.update(str(center.longitude).encode())
    if time_bounds.start_time:
        m.update(time_bounds.start_time.isoformat().encode())
    if time_bounds.end_time:
        m.update(time_bounds.end_time.isoformat().encode())
    if bounds:
        if bounds.max_latitude:
            m.update(str(bounds.max_latitude).encode())
        if bounds.min_latitude:
            m.update(str(bounds.min_latitude).encode())
        if bounds.max_longitude:
            m.update(str(bounds.max_longitude).encode())
        if bounds.min_longitude:
            m.update(str(bounds.min_longitude).encode())
    move_data = track.track.get_moving_data()
    m.update(str(move_data.moving_distance).encode())
    m.update(str(move_data.stopped_distance).encode())
    ele_extremenes = track.track.get_elevation_extremes()
    if ele_extremenes.maximum:
        m.update(str(ele_extremenes.maximum).encode())
    if ele_extremenes.minimum:
        m.update(str(ele_extremenes.minimum).encode())
    return m.hexdigest()
