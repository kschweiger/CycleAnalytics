from datetime import date, timedelta
from typing import Literal

import pandas as pd


def get_nice_timedelta_isoformat(time: str) -> str:
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


def format_timedelta(td: timedelta) -> str:
    """
    Format a timedelta object as a string in HH:MM:SS format.

    :param td: Timedelta object to be formatted.

    :return: Formatted string representing the timedelta in HH:MM:SS format.
    """
    seconds = td.seconds
    hours = int(seconds / 3600)
    seconds -= hours * 3600
    minutes = int(seconds / 60)
    seconds -= minutes * 60

    if td.days > 0:
        hours += 24 * td.days

    return "{0:02d}:{1:02d}:{2:02d}".format(hours, minutes, seconds)


def compare_values(diff: float, simularity_threshold: float) -> Literal[-1, 0, 1]:
    if abs(diff) <= simularity_threshold:
        return 0
    if diff < simularity_threshold:
        return -1
    else:
        return 1


def get_month_mapping() -> dict[int, str]:
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


def find_closest_elem_to_poi(
    data: pd.DataFrame, lat: float, lng: float, greedy: bool = True
) -> int:
    """
    Find the colosest element in the passed data to the passed lat and lng
    values.

    :param data: Dataframe containing *latitude* and *longitude* columns
    :param lat: Reference latitude
    :param lng: Reference longitude
    :param greedy: If True the search will stop as soon as the residuals start
                   to grow again, defaults to True
    :raises RuntimeError: If nothing can be found. This is not expected
    :return: Index in the dataframe closest to the passed lat/lng values
    """

    min_res_sum = 1e10
    idx_min = None
    for i, rcrd in enumerate(data.to_dict("records")):
        res_lat = abs(rcrd["latitude"] - lat)
        res_lng = abs(rcrd["longitude"] - lng)
        res_sum = res_lat + res_lng
        if res_sum < min_res_sum:
            min_res_sum = res_sum
            idx_min = i
        if greedy and res_sum > min_res_sum:
            break

    if idx_min is None:
        raise RuntimeError("Something want wrong here...")

    return idx_min
