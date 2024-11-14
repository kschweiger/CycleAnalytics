from collections import deque
from datetime import timedelta

from flask import (
    current_app,
)
from geo_track_analyzer.model import SegmentOverview

from cycle_analytics.utils.base import format_timedelta, unwrap


def segment_summary(segment_overviews: list[SegmentOverview], show_all: bool = True):
    colors = current_app.config.style.color_sequence
    segment_table_header = [
        # "#",
        "Distance [km]",
        "Max velocity [km/h]",
        "Avg velocity [km/h]",
        "Duration",
    ]
    segment_table_data = []
    segment_colors = []
    color_deque = deque(colors)
    for idx_segment, segment_overview in enumerate(segment_overviews):
        segment_table_data.append(
            [
                # idx_segment,
                round(segment_overview.moving_distance / 1000, 2),
                round(unwrap(segment_overview.max_velocity_kmh), 2),
                round(unwrap(segment_overview.avg_velocity_kmh), 2),
                format_timedelta(
                    timedelta(seconds=segment_overview.moving_time_seconds)
                ),
            ]
        )
        segment_colors.append(color_deque[0])
        color_deque.rotate(-1)
    return (
        segment_table_header,
        segment_table_data,
        segment_colors,
    )
