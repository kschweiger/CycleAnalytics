import json
import logging
from enum import StrEnum, auto

from flask import Blueprint, flash, render_template, request
from geo_track_analyzer.model import ZoneInterval, Zones
from pydantic import ValidationError

from cycle_analytics.cache import cache
from cycle_analytics.database.modifier import update_zones
from cycle_analytics.database.retriever import get_zones_for_metric

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

    if request.method == "POST":
        intervals = []
        for i in range(1, int(request.form.get("count_zones")) + 1):  # type: ignore
            zone_color = request.form.get(f"color_{i}", None)
            if zone_color == "":
                zone_color = None
            intervals.append(
                ZoneInterval(
                    name=request.form.get(f"name_{i}", None),
                    start=request.form.get(f"start_{i}", None),  # type: ignore
                    end=request.form.get(f"end_{i}", None),  # type: ignore
                    color=zone_color,  # type: ignore
                )
            )
        try:
            post_zones = Zones(intervals=intervals)
        except ValidationError:
            flash(
                "Invalid zone definition. Make sure that consecutive zones start and "
                "end with the same value"
            )
        else:
            update_zones(post_zones, zone_metric.value)
            print(post_zones)

    zones = get_zones_for_metric(zone_metric.value)
    if not zones:
        zones = Zones(
            intervals=[
                ZoneInterval(start=None, end=100),
                ZoneInterval(start=100, end=None),
            ]
        )

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
