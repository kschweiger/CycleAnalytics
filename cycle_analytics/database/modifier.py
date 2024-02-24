from typing import Literal

from cycle_analytics.model.goal import AggregationType

from .model import DatabaseGoal, DatabaseSegment
from .model import db as orm_db


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


def modify_segment_visited_flag(id_segment: int, visited: bool) -> bool:
    segment: DatabaseSegment | None = orm_db.session.get(DatabaseSegment, id_segment)
    if not segment:
        return False

    segment.visited = visited
    orm_db.session.add(segment)
    orm_db.session.commit()
    return True
