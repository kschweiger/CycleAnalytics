from dataclasses import dataclass
from datetime import date
from typing import Dict, Optional


@dataclass
class LastRide:
    date: date
    data: Dict[str, str]
    thumbnails: Optional[list[str]]


@dataclass
class MapPathData:
    latitudes: str
    longitudes: str


@dataclass
class MapData:
    path: MapPathData


@dataclass
class GoalInfoData:
    name: str
    goal: str
    threshold: str
    value: int | float
    progress: float
    reached: int
    description: None | str


@dataclass
class GoalDisplayData:
    goal_id: str
    info: GoalInfoData
    progress_bar: bool
