import pytest
from geo_track_analyzer.model import ZoneInterval

from cycle_analytics.settings import Action, _update_zones


@pytest.mark.parametrize(
    ("intervals_in", "intervals_out", "action"),
    [
        (
            [ZoneInterval(start=None, end=100), ZoneInterval(start=100, end=None)],
            [ZoneInterval(start=None, end=100), ZoneInterval(start=100, end=None)],
            None,
        ),
        (
            [ZoneInterval(start=None, end=100), ZoneInterval(start=100, end=None)],
            [
                ZoneInterval(start=None, end=100),
                ZoneInterval(start=100, end=101),
                ZoneInterval(start=101, end=None),
            ],
            Action.ADD,
        ),
        (
            [
                ZoneInterval(name="Z1", start=None, end=100),
                ZoneInterval(name="Z2", start=100, end=None),
            ],
            [
                ZoneInterval(name="Z1", start=None, end=100),
                ZoneInterval(name="Z2", start=100, end=101),
                ZoneInterval(name="Added Zone", start=101, end=None),
            ],
            Action.ADD,
        ),
        (
            [
                ZoneInterval(start=None, end=100),
                ZoneInterval(start=100, end=101),
                ZoneInterval(start=101, end=None),
            ],
            [
                ZoneInterval(start=None, end=100),
                ZoneInterval(start=100, end=None),
            ],
            Action.REMOVE,
        ),
    ],
)
def test_update_zones(
    intervals_in: list[ZoneInterval],
    intervals_out: list[ZoneInterval],
    action: None | Action,
) -> None:
    assert intervals_out == _update_zones(intervals_in, action)
