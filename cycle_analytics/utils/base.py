import logging
import re
from copy import copy
from datetime import date, timedelta
from typing import Literal, TypeVar

import pandas as pd
import tldextract
from flask import url_for

from cycle_analytics.database.model import DatabaseLocation
from cycle_analytics.model.base import MapMarker

T = TypeVar("T")

logger = logging.getLogger(__name__)


def none_or_round(value: None | float, digits: int = 2) -> None | float:
    return None if value is None else round(value, digits)


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


def unwrap(data: None | T) -> T:
    if data is None:
        raise RuntimeError("Data is None")
    return data


def format_float(num: float) -> str:
    """Formats a float to a string, removing decimal points if possible.

    :param num: The float to format.

    :return: A string representation of the float, with decimal points removed
    if possible.
    """

    # Check if the float can be rounded to an integer without loss of precision.
    if int(num) == num:
        return str(int(num))
    else:
        # Use f-strings to format the float with two decimal places.
        return f"{num:.2f}"


def format_description(raw_text: str) -> str:
    """
    Takes a raw string and fomrats it to a string with html formatting.
    Currently does:
    - FInd links and transform them to html links with <a>
    :param raw_text: Raw text to format
    :return: Text enriched with html formatting
    """
    out_text = copy(raw_text)

    pattern_link = r"https?://\S+|www\.\S+"
    matches_link = re.findall(pattern_link, raw_text)
    for match in matches_link:
        hyperlink = match
        res = tldextract.extract(hyperlink)
        out_text = out_text.replace(
            hyperlink, f'<a href="{hyperlink}">{res.domain}.{res.suffix}</a>'
        )

    return out_text


def format_seconds(
    seconds: int,
    to: Literal["seconds", "minutes", "hours"],
    format: Literal["minimal", "complete", "truncated"],
) -> str:
    if seconds == 0:
        return "0" if format == "minimal" else "0 seconds"
    if to == "seconds":
        if format == "minimal":
            return str(seconds)
        else:
            sec_kw = "second" if seconds == 1 else "seconds"
            return f"{seconds} {sec_kw}"
    elif to == "minutes":
        if format == "minimal":
            return format_timedelta(timedelta(seconds=seconds))
        else:
            minutes = seconds // 60
            _seconds = seconds - (minutes * 60)
            min_kw = "minute" if minutes == 1 else "minutes"
            sec_kw = "second" if _seconds == 1 else "seconds"
            elements = []
            if minutes >= 1 or format == "complete":
                elements.append(f"{minutes} {min_kw}")
            if _seconds >= 1 or format == "complete":
                elements.append(f"{_seconds} {sec_kw}")
            return " and ".join(elements)
    elif to == "hours":
        if format == "minimal":
            return format_timedelta(timedelta(seconds=seconds))
        else:
            hours = seconds // (60 * 60)
            _seconds = seconds - (hours * 60 * 60)
            minutes = _seconds // 60
            _seconds = _seconds - (minutes * 60)
            elements = []
            h_kw = "hour" if hours == 1 else "hours"
            min_kw = "minute" if minutes == 1 else "minutes"
            sec_kw = "second" if _seconds == 1 else "seconds"
            if hours >= 1 or format == "complete":
                elements.append(f"{hours} {h_kw}")
            if minutes >= 1 or format == "complete":
                elements.append(f"{minutes} {min_kw}")
            if _seconds >= 1 or format == "complete":
                elements.append(f"{_seconds} {sec_kw}")
            return " and ".join(elements)

    else:
        raise NotImplementedError("formatting to %s is not supported", to)


def convert_locations_to_markers(
    locations: list[DatabaseLocation], deletable: bool = False
) -> list[MapMarker]:
    location_markers = []
    for location in locations:
        text = f"<b>{location.name}</b>"
        if location.description:
            text += f": {location.description}"
        _href = url_for("locations.show", id_location=location.id)
        text += f"<br><div><a href='{_href}'>Details</a></div> "
        if deletable:
            _href = url_for("locations.delete_location", id_location=location.id)
            text += f"<div><a href='{_href}'>Delete</a></div>"
        location_markers.append(
            MapMarker(
                latitude=location.latitude,
                longitude=location.longitude,
                popup_text=text,
                color="blue",
                color_idx=0,
            )
        )

    return location_markers


def get_curr_and_prev_month_date_ranges(
    curr_year: int,
    curr_month: int,
) -> tuple[tuple[date, date], tuple[date, date]]:
    curr_month_start = date(curr_year, curr_month, 1)
    if curr_month == 12:
        curr_month_end = date(curr_year + 1, 1, 1) - timedelta(days=1)
    else:
        curr_month_end = date(curr_year, curr_month + 1, 1) - timedelta(days=1)

    if curr_month == 1:
        last_year = curr_month_start.year - 1
        last_month_start = date(last_year, 12, 1)
        last_month_end = date(last_year, 12, 31)
    else:
        last_month_end = curr_month_start - timedelta(days=1)
        last_month_start = date(last_month_end.year, last_month_end.month, 1)

    logger.debug("Curr. month:  %s - %s", curr_month_start, curr_month_end)
    logger.debug("Last month:  %s - %s", last_month_start, last_month_end)

    return (curr_month_start, curr_month_end), (last_month_start, last_month_end)
