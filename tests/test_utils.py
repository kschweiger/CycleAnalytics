from datetime import date

import pytest
from pandas import Timedelta

from cycle_analytics.utils import compare_values, get_date_range_from_year_month


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


@pytest.mark.parametrize(
    ("year", "month", "exp_range"),
    [
        (2022, None, (date(2022, 1, 1), date(2022, 12, 31))),
        (2022, 1, (date(2022, 1, 1), date(2022, 1, 31))),
        (2022, 2, (date(2022, 2, 1), date(2022, 2, 28))),
        (2022, 12, (date(2022, 12, 1), date(2022, 12, 31))),
    ],
)
def test_daterange(year, month, exp_range):
    assert get_date_range_from_year_month(year, month) == exp_range
