from dataclasses import dataclass
from datetime import date
from typing import Dict, Optional

from track_analyzer.track import Track

from cycle_analytics.enums import BikeType, FrameMaterial


@dataclass
class Bike:
    name: str
    brand: str
    model: str
    material: FrameMaterial
    type: BikeType
    purchased: date
    type_specification: None | str
    weight: None | float
    decommissioned: None | date


@dataclass
class LatLngBounds:
    min_latitude: float
    max_latitude: float
    min_longitude: float
    max_longitude: float


@dataclass
class SegmentData:
    id: int
    name: str
    description: None | str
    type: str
    difficulty: None | str
    distance: float
    visited: bool
    min_elevation: None | float
    max_elevation: None | float
    uphill_elevation: None | float
    downhill_elevation: None | float
    track: Track
    bounds: LatLngBounds


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


@dataclass
class GoalDisplayData:
    goal_id: str
    info: GoalInfoData
    progress_bar: bool


def bike_from_dict(dict: Dict) -> Bike:
    if isinstance(dict["purchase_date"], str):
        p_date = date.fromisoformat(dict["purchase_date"])
    else:
        p_date = dict["purchase_date"]

    d_date: None | date
    if dict["decommission_date"] is None:
        d_date = None
    elif isinstance(dict["decommission_date"], str):
        d_date = date.fromisoformat(dict["decommission_date"])
    else:
        d_date = dict["decommission_date"]

    return Bike(
        name=dict["bike_name"],
        brand=dict["bike_brand"],
        model=dict["bike_model"],
        material=FrameMaterial(dict["bike_frame_material"].lower()),
        type=BikeType(dict["bike_type"].lower()),
        purchased=p_date,
        type_specification=dict["bike_type_specification"],
        weight=dict["bike_weight"],
        decommissioned=d_date,
    )
