import logging

from flask import current_app, flash
from track_analyzer.enhancer import get_enhancer
from track_analyzer.exceptions import APIHealthCheckFailedError, APIResponseError
from track_analyzer.track import ByteTrack, Track

from cycle_analytics.db import get_db
from cycle_analytics.queries import (
    get_last_track_id,
    ride_track_id,
    track_has_overview,
    update_track,
    update_track_overview,
)

numeric = int | float
logger = logging.getLogger(__name__)


def add_track_to_db(data: bytes, replace: bool, id_ride: int) -> None:
    raw_table_name = current_app.config.tables_as_settings[
        current_app.config.defaults.raw_track_table
    ].name
    enhanced_table_name = current_app.config.tables_as_settings[
        current_app.config.defaults.track_table
    ].name

    db = get_db()

    enhanced_id = None

    if replace:
        insert_raw_id = ride_track_id(
            id_ride,
            raw_table_name,
        )
        enhanced_id = ride_track_id(
            id_ride,
            enhanced_table_name,
        )
        if insert_raw_id is None:
            raise RuntimeError(
                "Can not update track because ride has no track yet. Use the "
                "regular adder instead"
            )

        logger.debug("Updating raw track at track_id: %s", insert_raw_id)
        insert_succ_track = update_track(
            raw_table_name, insert_raw_id, id_ride, data  # type: ignore
        )
        err = "Could not update track"
    else:
        insert_succ_track, err = db.insert(
            current_app.config.tables_as_settings[
                current_app.config.defaults.raw_track_table
            ],
            [[id_ride, data]],
        )

    if insert_succ_track:
        flash("Track updated" if replace else "Track added", "alert-success")
        enhance_and_insert_track(data=data, id_ride=id_ride, enhance_id=enhanced_id)
    else:
        err = "No error msg available" if err is None else err
        flash(
            f"Track could not be {'updated' if replace else 'added'}: {err[0:250]}",
            "alert-danger",
        )


def enhance_track(
    track: Track,
) -> tuple[None, None] | tuple[bytes, list[numeric | None]]:
    track_data = None
    track_overview_data = None

    enhancer = None
    try:
        enhancer = get_enhancer(current_app.config.external.track_enhancer.name)(
            url=current_app.config.external.track_enhancer.url,
            **current_app.config.external.track_enhancer.kwargs.to_dict(),
        )  # type: ignore
    except APIHealthCheckFailedError:
        logger.warning("Enhancer not available. Skipping elevation profile")
        flash("Track could not be enhanced - API not available", "alert-danger")
        return None, None

    try:
        enhancer.enhance_track(track.track, True)
    except APIResponseError:
        logger.error("Could not enhance track with elevation")
        return None, None

    track_data = track.get_xml().encode()

    this_track_overview = track.get_track_overview()
    bounds = track.track.get_bounds()
    track_overview_data = [
        this_track_overview.moving_time_seconds,
        this_track_overview.total_time_seconds,
        this_track_overview.moving_distance,
        this_track_overview.total_distance,
        this_track_overview.max_velocity,
        this_track_overview.avg_velocity,
        this_track_overview.max_elevation,
        this_track_overview.min_elevation,
        this_track_overview.uphill_elevation,
        this_track_overview.downhill_elevation,
        this_track_overview.moving_distance_km,
        this_track_overview.total_distance_km,
        this_track_overview.max_velocity_kmh,
        this_track_overview.avg_velocity_kmh,
        bounds.min_latitude,
        bounds.max_latitude,
        bounds.min_longitude,
        bounds.max_longitude,
    ]

    return track_data, track_overview_data


def enhance_and_insert_track(data: bytes, id_ride: int, enhance_id: None | int) -> None:
    logger.info("Enhancing: id_ride = %s, enhance_id = %s", id_ride, enhance_id)
    db = get_db()
    enhanced_table_name = current_app.config.tables_as_settings[
        current_app.config.defaults.track_table
    ].name

    track = ByteTrack(data)
    enhanced_track_data, _track_overview_data = enhance_track(track)

    if enhanced_track_data is None:
        return

    if enhance_id is not None:
        logger.debug("Updating enhanced track at track_id: %s", enhance_id)
        enhance_insert_succ_track = update_track(
            enhanced_table_name, enhance_id, id_ride, enhanced_track_data
        )
        err = ("Could not update enhanced track",)
    else:
        enhance_insert_succ_track, err = db.insert(
            current_app.config.tables_as_settings[
                current_app.config.defaults.track_table
            ],
            [[id_ride, enhanced_track_data]],
        )
    if not enhance_insert_succ_track:
        flash(
            "Enhanced Track could not be inserted: " f"{err[0:250]}",  # type: ignore
            "alert-danger",
        )
        return

    flash("Enhanced Track added", "alert-success")

    if _track_overview_data is None:
        raise RuntimeError

    id_track = get_last_track_id(
        current_app.config.defaults.track_table, "id_track", True
    )
    track_overview_data = [id_track] + _track_overview_data
    err: str | None
    if enhance_id is not None:
        if track_has_overview(
            enhance_id,
            current_app.config.tables_as_settings[
                current_app.config.defaults.track_overview_table
            ].name,
        ):
            overview_table = current_app.config.tables_as_settings[
                current_app.config.defaults.track_overview_table
            ]
            cols = [c.name for c in overview_table.columns][1:]
            overview_insert_succ_track = False
            overview_insert_succ_track = update_track_overview(
                table_name=overview_table.name,
                id_track=enhance_id,
                cols=cols,
                data=track_overview_data[1:],
            )
            err = "Track overview data could not be updated "
        else:
            overview_insert_succ_track, err = db.insert(
                current_app.config.tables_as_settings[
                    current_app.config.defaults.track_overview_table
                ],
                [[enhance_id] + _track_overview_data],
            )

    else:
        overview_insert_succ_track, err = db.insert(
            current_app.config.tables_as_settings[
                current_app.config.defaults.track_overview_table
            ],
            [track_overview_data],
        )
    if overview_insert_succ_track:
        flash(
            f"Overview inserted for track {id_track}",
            "alert-success",
        )
    else:
        err = "No error msg available" if err is None else err
        flash(
            "Overview could not be generated: " f"{err[0:250]}",  # type: ignore
            "alert-danger",
        )
