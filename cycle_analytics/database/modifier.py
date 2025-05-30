import logging
from datetime import datetime
from typing import Literal

from geo_track_analyzer.model import Zones
from sqlalchemy import select

from ..model.goal import AggregationType
from .model import (
    DatabaseGoal,
    DatabaseSegment,
    DatabaseTrack,
    DatabaseZoneInterval,
    TrackOverview,
)
from .model import db as orm_db

logger = logging.getLogger(__name__)


def modify_goal_status(id_goal: int, active: bool = True) -> bool:
    goal = orm_db.session.get(DatabaseGoal, id_goal)

    if not goal:
        return False

    goal.active = active
    orm_db.session.add(goal)
    orm_db.session.commit()
    return True


def modify_manual_goal_value_count(
    id_goal: int, action: Literal["increase", "decrease"]
) -> bool:
    goal = orm_db.session.get(DatabaseGoal, id_goal)
    if not goal:
        return False

    if AggregationType(goal.aggregation_type) != AggregationType.COUNT:
        raise ValueError("Can only modify goals with a count aggregation method")

    if action == "increase":
        if goal.value is None:
            goal.value = 1
        else:
            goal.value += 1
    else:
        if goal.value is None or goal.value < 1:
            raise ValueError("Cannot decrease goals without value")
        goal.value -= 1

    orm_db.session.add(goal)
    orm_db.session.commit()
    return True


def update_manual_goal_value(id_goal: int, new_value: float) -> bool:
    goal = orm_db.session.get(DatabaseGoal, id_goal)
    if not goal:
        return False

    goal.value = new_value
    orm_db.session.add(goal)
    orm_db.session.commit()
    return True


def modify_segment_visited_flag(id_segment: int, visited: bool) -> bool:
    segment: DatabaseSegment | None = orm_db.session.get(DatabaseSegment, id_segment)
    if not segment:
        return False

    segment.visited = visited
    orm_db.session.add(segment)
    orm_db.session.commit()
    return True


def switch_overview_of_interest_flag(id_overview: int) -> bool:
    overview: TrackOverview | None = orm_db.session.get(TrackOverview, id_overview)
    if not overview:
        return False

    overview.of_interest = not overview.of_interest
    orm_db.session.add(overview)
    orm_db.session.commit()

    return True


def update_zones(zones: Zones, metric: str) -> bool:
    stmt = select(DatabaseZoneInterval).where(DatabaseZoneInterval.metric == metric)
    curr_zones = orm_db.session.execute(stmt).scalars().all()
    print(curr_zones)
    for curr_zone in curr_zones:
        print(curr_zone)
        orm_db.session.delete(curr_zone)

    new_zones = []
    for i, interval in enumerate(zones.intervals):
        new_zones.append(
            DatabaseZoneInterval(
                id=i,
                metric=metric,
                name=interval.name,
                interval_start=interval.start,
                interval_end=interval.end,
                color=interval.color,
            )
        )
    orm_db.session.add_all(new_zones)

    orm_db.session.commit()
    return True


def update_track_content(id_track: int, new_content: bytes) -> bool:
    db_track = orm_db.session.get(DatabaseTrack, id_track)
    if db_track is None:
        logger.error("Invalid track id %s", id_track)
        return False
    db_track.content = new_content
    db_track.added = datetime.now()
    try:
        orm_db.session.commit()
    except TypeError:
        logger.error("Cannot convert %s to binary", new_content)
        return False

    return True


def update_track_overview(id_track: int, new_overviews: list[TrackOverview]) -> bool:
    overviews = orm_db.session.query(TrackOverview).filter_by(id_track=id_track).all()
    for overview in overviews:
        orm_db.session.delete(overview)
    orm_db.session.add_all(new_overviews)
    orm_db.session.commit()

    return True
