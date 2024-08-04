from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Dict, Optional

from geo_track_analyzer.model import BaseModel


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
    color: str = "#20c997"


@dataclass
class MapData:
    paths: list[MapPathData]


@dataclass
class MapMarker:
    latitude: float
    longitude: float
    popup_text: str
    color: str
    color_idx: int


@dataclass
class ManualGoalSetting:
    steps: bool
    decreasable: bool


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
    manual_setting: None | ManualGoalSetting


@dataclass
class GoalDisplayData:
    goal_id: str
    info: GoalInfoData
    progress_bar: bool


class RideOverviewContainer(BaseModel):
    id_ride: int
    ride_date: datetime
    ride_duration: None | timedelta
    total_duration: timedelta
    distance_raw: float
    terrain_type: str
    bike: str
    overview_distance: None | float
    overview_avg_vel: None | float
    overview_uphill: None | float
    overview_downhill: None | float
