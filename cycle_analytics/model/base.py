from dataclasses import dataclass
from datetime import date
from typing import Dict, Optional


@dataclass
class LatLngBounds:
    min_latitude: float
    max_latitude: float
    min_longitude: float
    max_longitude: float


@dataclass
class LastRide:
    id: int
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
class MapMarker:
    latitude: float
    longitude: float
    popup_text: str
    color: str
    color_idx: int


@dataclass
class GoalInfoData:
    name: str
    goal: str
    threshold: float
    value: int | float
    progress: float
    reached: int
    description: None | str
    active: bool
    is_manual: bool
    decreasable: bool


@dataclass
class GoalDisplayData:
    goal_id: str
    info: GoalInfoData
    progress_bar: bool
