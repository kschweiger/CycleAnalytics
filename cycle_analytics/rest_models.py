from pydantic import BaseModel


class SegmentsInBoundsRequest(BaseModel):
    ids_on_map: list[int]
    ne_latitude: float
    ne_longitude: float
    sw_latitude: float
    sw_longitude: float


class SegmentForMap(BaseModel):
    segment_id: int
    name: str
    points: list[tuple[float, float]]
    url: str
    type: str
    difficulty: str
    color: str


class SegmentsInBoundsResponse(BaseModel):
    segments: list[SegmentForMap]
