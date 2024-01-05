import logging
from datetime import datetime

from flask import current_app, flash
from track_analyzer.enhancer import get_enhancer
from track_analyzer.exceptions import APIHealthCheckFailedError, APIResponseError
from track_analyzer.track import Track

from cycle_analytics.database.converter import initialize_overviews
from cycle_analytics.database.model import DatabaseTrack

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
