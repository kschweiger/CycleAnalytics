from datetime import date, timedelta
from typing import Literal


def get_nice_timedelta_isoformat(time: str):
    time_ = time.split("T")
    days = time_[0].replace("P", "").replace("D", "")
    if "Y" in days or "M" in days:
        raise NotImplementedError("Years and month not implemented: Got %s" % time)
    days_ = int(days)
    time = time_[1]
    vals = []
    for char in ["H", "M", "S"]:
        time_ = time.split(char)
        time = time_[1]
        vals.append(int(time_[0]))
    assert len(vals) == 3
    hours, mins, secs = tuple(vals)
    hours += 24 * days_
    return "{0:02d}:{1:02d}:{2:02d}".format(hours, mins, secs)


def compare_values(diff, simularity_threshold) -> Literal[-1, 0, 1]:
    if abs(diff) <= simularity_threshold:
        return 0
    if diff < simularity_threshold:
        return -1
    else:
        return 1


def get_month_mapping():
    return {
        1: "January",
        2: "February",
        3: "March",
        4: "April",
        5: "May",
        6: "June",
        7: "July",
        8: "August",
        9: "September",
        10: "October",
        11: "November",
        12: "December",
    }


def get_date_range_from_year_month(year: int, month: None | int) -> tuple[date, date]:
    if month is None:
        return date(year, 1, 1), date(year, 12, 31)
    else:
        if month == 12:
            return date(year, 12, 1), date(year, 12, 31)
        else:
            return date(year, month, 1), date(year, month + 1, 1) - timedelta(days=1)
