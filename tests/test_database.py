from flask import Flask, current_app

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
