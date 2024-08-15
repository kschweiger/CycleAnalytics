import json
import logging
from enum import StrEnum, auto

from flask import Blueprint, flash, render_template, request
from geo_track_analyzer.model import ZoneInterval, Zones

from cycle_analytics.cache import cache

logger = logging.getLogger(__name__)

bp = Blueprint("settings", __name__, url_prefix="/settings")


class ZoneMetric(StrEnum):
    HEARTRATE = auto()
    POWER = auto()
    CADENCE = auto()
    VELOCITY = auto()


class Action(StrEnum):
    ADD = auto()
    REMOVE = auto()


def _update_zones(
    intervals: list[ZoneInterval], action: None | Action
) -> list[ZoneInterval]:
    if len(intervals) <= 2 and action is not Action.ADD:
        return intervals

    if action is Action.ADD:
        pre_start = intervals[-1].start
        assert pre_start is not None
        intervals[-1].end = pre_start + 1
        intervals.append(
            ZoneInterval(
                name=None if intervals[-1].name is None else "Added Zone",
                start=pre_start + 1,
                end=None,
            )
        )
    elif action is Action.REMOVE:
        print("asdasd")
        if len(intervals) > 2:
            print(intervals)
            intervals = intervals[:-1]
            intervals[-1].end = None
            print(intervals)
        else:
            logger.error("Can not remove intervals if only two are passed")
    return intervals


@bp.route("/get_zone_form/", methods=["POST"])
def get_zone_form() -> dict[str, str]:
    action = request.args.get("action", None)
    if action is not None:
        action = Action(action)

    logger.debug("Action: %s", action)

    payload = request.get_json()
    disable_rm_btn = False
    intervals = [ZoneInterval(**json.loads(zone)) for zone in payload["intervals"]]
    if len(intervals) < 2:
        logger.error("Pass at least two zones")

    zones = Zones(intervals=_update_zones(intervals, action))
    outgoing_payload = {"intervals": [i.json() for i in zones.intervals]}
    if len(zones.intervals) == 2:
        disable_rm_btn = True
    _rendered_temple = render_template(
        "utils/zone_template.html",
        zones=zones,
        payload=outgoing_payload,
        disable_rm_btn=disable_rm_btn,
    )
    return {"data": _rendered_temple}


@bp.route("/modify_zones/<metric>", methods=("GET", "POST"))
def modify_zones(metric: str) -> str:
    zone_metric = ZoneMetric(metric)

    # TEMP:
    zones = Zones(
        intervals=[
            ZoneInterval(start=None, end=100),
            ZoneInterval(start=100, end=150),
            ZoneInterval(start=150, end=None),
        ]
    )
    # TEMP:

    return render_template(
        "utils/modify_zones.html",
        metric=zone_metric,
        zones=zones,
        inital_payload={"intervals": [i.json() for i in zones.intervals]},
        active_page="settings",
    )


@bp.route("/zones", methods=("GET", "POST"))
def zones() -> str:
    return render_template(
        "zones.html",
        active_page="settings",
    )


@bp.route("/", methods=("GET", "POST"))
def main() -> str:
    if request.method == "POST":
        if request.form.get("reset_cache") is not None:
            logger.warning("Resetting cache")
            cache.clear()
            flash("Cache cleared", "alert-warning")

    return render_template(
        "settings.html",
        active_page="settings",
    )
