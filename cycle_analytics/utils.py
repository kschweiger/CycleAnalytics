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
