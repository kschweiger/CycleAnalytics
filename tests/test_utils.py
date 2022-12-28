import pytest
from pandas import Timedelta

from cycle_analytics.utils import compare_values


@pytest.mark.parametrize(
    ("val1", "val2", "func", "thresh", "exp"),
    [
        (50, 20, lambda x, y: x - y, 5, 1),
        (20, 50, lambda x, y: x - y, 5, -1),
        (20, 22, lambda x, y: x - y, 5, 0),
        (
            Timedelta(days=0, hours=5, minutes=0, seconds=0),
            Timedelta(days=0, hours=20, minutes=0, seconds=0),
            lambda x, y: x - y,
            Timedelta(minutes=15),
            -1,
        ),
        (
            Timedelta(days=0, hours=20, minutes=0, seconds=0),
            Timedelta(days=0, hours=5, minutes=0, seconds=0),
            lambda x, y: x - y,
            Timedelta(minutes=15),
            1,
        ),
        (
            Timedelta(days=0, hours=5, minutes=10, seconds=0),
            Timedelta(days=0, hours=5, minutes=0, seconds=0),
            lambda x, y: x - y,
            Timedelta(minutes=15),
            0,
        ),
    ],
)
def test_compare_values(val1, val2, func, thresh, exp):
    assert compare_values(func(val1, val2), thresh) == exp
