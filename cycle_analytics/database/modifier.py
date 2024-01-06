from .model import DatabaseGoal, DatabaseSegment
from .model import db as orm_db


def modify_goal_status(id_goal: int, active: bool = True) -> bool:
    goal = DatabaseGoal.query.get(id_goal)
    if not goal:
        return False

    goal.active = active
    orm_db.session.add(goal)
    orm_db.session.commit()
    return True


def modify_segment_visited_flag(id_segment: int, visited: bool) -> bool:
    segment: DatabaseSegment | None = DatabaseSegment.query.get(id_segment)
    if not segment:
        return False

    segment.visited = visited
    orm_db.session.add(segment)
    orm_db.session.commit()
    return True
