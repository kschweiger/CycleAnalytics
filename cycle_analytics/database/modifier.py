from .model import DatabaseGoal
from .model import db as orm_db


def modify_goal_status(id_goal: int, active: bool = True) -> bool:
    goal = DatabaseGoal.query.get(id_goal)
    if not goal:
        return False

    goal.active = active
    orm_db.session.add(goal)
    orm_db.session.commit()
    return True
