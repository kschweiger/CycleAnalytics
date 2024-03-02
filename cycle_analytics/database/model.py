from datetime import date, datetime, time, timedelta
from typing import Optional, Type

from flask_sqlalchemy import SQLAlchemy
from geo_track_analyzer import ByteTrack, Track
from sqlalchemy import Column
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    MappedAsDataclass,
    mapped_column,
    relationship,
)


class Base(DeclarativeBase, MappedAsDataclass):
    pass


db = SQLAlchemy(model_class=Base)

ride_event = db.Table(
    "rel_ride_event",
    Column("ride_id", db.Integer, db.ForeignKey("ride.id")),
    Column("event_id", db.Integer, db.ForeignKey("event.id")),
)

ride_track = db.Table(
    "rel_ride_track",
    Column("ride_id", db.Integer, db.ForeignKey("ride.id")),
    Column("track_id", db.Integer, db.ForeignKey("track.id")),
)

ride_note = db.Table(
    "rel_ride_note",
    Column("ride_id", db.Integer, db.ForeignKey("ride.id")),
    Column("note_id", db.Integer, db.ForeignKey("ride_note.id")),
)

location_track = db.Table(
    "rel_location_track",
    Column("location_id", db.Integer, db.ForeignKey("location.id")),
    Column("track_id", db.Integer, db.ForeignKey("track.id")),
)


class TerrainType(Base):
    __tablename__ = "terrain_type"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, init=False)
    text: Mapped[str] = mapped_column(db.String, unique=True, nullable=False)

    def __str__(self) -> str:
        return self.text


class TypeSpecification(Base):
    __tablename__ = "type_specification"

    id: Mapped[int] = mapped_column(
        db.Integer, primary_key=True, autoincrement=True, init=False
    )
    text: Mapped[str] = mapped_column(unique=True, nullable=False)

    def __str__(self) -> str:
        return self.text


class Material(Base):
    __tablename__ = "material"

    id: Mapped[int] = mapped_column(
        db.Integer, primary_key=True, autoincrement=True, init=False
    )
    text: Mapped[str] = mapped_column(unique=True, nullable=False)

    def __str__(self) -> str:
        return self.text


class EventType(Base):
    __tablename__ = "event_type"
    id: Mapped[int] = mapped_column(
        db.Integer, primary_key=True, autoincrement=True, init=False
    )
    text: Mapped[str] = mapped_column(unique=True, nullable=False)

    def __str__(self) -> str:
        return self.text


class Severity(Base):
    __tablename__ = "severity"

    id: Mapped[int] = mapped_column(
        db.Integer, primary_key=True, autoincrement=True, init=False
    )
    text: Mapped[str] = mapped_column(unique=True, nullable=False)

    def __str__(self) -> str:
        return self.text


class SegmentType(Base):
    __tablename__ = "segment_type"

    id: Mapped[int] = mapped_column(
        db.Integer, primary_key=True, autoincrement=True, init=False
    )
    text: Mapped[str] = mapped_column(unique=True, nullable=False)

    def __str__(self) -> str:
        return self.text


class Difficulty(Base):
    __tablename__ = "difficulty"

    id: Mapped[int] = mapped_column(
        db.Integer, primary_key=True, autoincrement=True, init=False
    )
    text: Mapped[str] = mapped_column(unique=True, nullable=False)

    def __str__(self) -> str:
        return self.text


CategoryModelType = Type[
    TerrainType
    | TypeSpecification
    | Material
    | EventType
    | Severity
    | SegmentType
    | Difficulty
]


class RideNote(Base):
    __tablename__ = "ride_note"

    id: Mapped[int] = mapped_column(db.Integer, primary_key=True, init=False)
    text: Mapped[str] = mapped_column(db.TEXT, nullable=False)


class TrackOverview(Base):
    __tablename__ = "track_overview"
    __table_args__ = (db.UniqueConstraint("id_track", "id_segment"),)

    id: Mapped[int] = mapped_column(
        db.Integer, primary_key=True, autoincrement=True, init=False
    )
    id_track: Mapped[int] = mapped_column(
        db.Integer, db.ForeignKey("track.id"), nullable=False
    )
    id_segment: Mapped[Optional[int]] = mapped_column(db.Integer, nullable=True)
    moving_time_seconds: Mapped[float] = mapped_column(db.Float, nullable=False)
    total_time_seconds: Mapped[float] = mapped_column(db.Float, nullable=False)
    moving_distance: Mapped[float] = mapped_column(db.Float, nullable=False)
    total_distance: Mapped[float] = mapped_column(db.Float, nullable=False)
    max_velocity: Mapped[float] = mapped_column(db.Float, nullable=False)
    avg_velocity: Mapped[float] = mapped_column(db.Float, nullable=False)
    max_elevation: Mapped[Optional[float]] = mapped_column(db.Float, nullable=True)
    min_elevation: Mapped[Optional[float]] = mapped_column(db.Float, nullable=True)
    uphill_elevation: Mapped[Optional[float]] = mapped_column(db.Float, nullable=True)
    downhill_elevation: Mapped[Optional[float]] = mapped_column(db.Float, nullable=True)
    moving_distance_km: Mapped[float] = mapped_column(db.Float, nullable=False)
    total_distance_km: Mapped[float] = mapped_column(db.Float, nullable=False)
    max_velocity_kmh: Mapped[float] = mapped_column(db.Float, nullable=False)
    avg_velocity_kmh: Mapped[float] = mapped_column(db.Float, nullable=False)
    bounds_min_lat: Mapped[float] = mapped_column(db.Float, nullable=False)
    bounds_max_lat: Mapped[float] = mapped_column(db.Float, nullable=False)
    bounds_min_lng: Mapped[float] = mapped_column(db.Float, nullable=False)
    bounds_max_lng: Mapped[float] = mapped_column(db.Float, nullable=False)
    of_interest: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=True)


class DatabaseTrack(Base):
    __tablename__: str = "track"
    __allow_unmapped__ = True

    id: Mapped[int] = mapped_column(db.Integer, primary_key=True, init=False)
    content: Mapped[bytes] = mapped_column(db.LargeBinary)
    added: Mapped[datetime] = mapped_column(db.DateTime(timezone=True))
    is_enhanced: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=False)

    overviews: list[TrackOverview] = db.relationship(
        "TrackOverview",
        backref="ride",
        lazy=True,
        cascade="all, delete",
        default_factory=lambda: [],
    )  # type: ignore

    def __repr__(self) -> str:
        return (
            f"DatabaseTrack(id={self.id}, added={self.added.isoformat()}, "
            f"is_enhanced={self.is_enhanced}, content={len(self.content)} elems, "
            f"n_overviews={len(self.overviews)})"
        )


class Bike(Base):
    __tablename__ = "bike"

    id: Mapped[int] = mapped_column(db.Integer, primary_key=True, init=False)
    name: Mapped[str] = mapped_column(db.String, unique=True, nullable=False)
    brand: Mapped[str] = mapped_column(db.String, nullable=False)
    model: Mapped[str] = mapped_column(db.String, nullable=False)

    id_material: Mapped[int] = mapped_column(
        db.Integer, db.ForeignKey("material.id"), nullable=False, init=False
    )
    material: Mapped[Material] = relationship(lazy=False)

    id_terraintype: Mapped[int] = mapped_column(
        db.Integer, db.ForeignKey("terrain_type.id"), nullable=False, init=False
    )
    terrain_type: Mapped[TerrainType] = relationship(lazy=False)

    id_specification: Mapped[int] = mapped_column(
        db.Integer, db.ForeignKey("type_specification.id"), nullable=False, init=False
    )
    specification: Mapped[TypeSpecification] = relationship(lazy=False)

    commission_date: Mapped[date] = mapped_column(db.Date())
    weight: Mapped[Optional[float]] = mapped_column(db.Float, default=None)
    decommission_date: Mapped[Optional[date]] = mapped_column(db.Date(), default=None)


class DatabaseEvent(Base):
    __tablename__: str = "event"

    id: Mapped[int] = mapped_column(db.Integer, primary_key=True, init=False)

    event_date: Mapped[date] = mapped_column(db.Date())
    id_event_type: Mapped[int] = mapped_column(
        db.Integer, db.ForeignKey("event_type.id"), nullable=False, init=False
    )
    event_type: Mapped[EventType] = relationship(backref="event", lazy=False)

    short_description: Mapped[str] = mapped_column(db.String, nullable=False)

    id_severity: Mapped[Optional[int]] = mapped_column(
        db.Integer, db.ForeignKey("severity.id"), nullable=True, init=False
    )
    severity: Mapped[Optional[Severity]] = relationship(
        "Severity", backref="event", lazy=False, default=None
    )

    id_bike: Mapped[Optional[int]] = mapped_column(
        db.Integer, db.ForeignKey("bike.id"), nullable=True, init=False
    )
    bike: Mapped[Optional[Bike]] = relationship(
        "Bike", backref="event", lazy=True, default=None
    )

    description: Mapped[Optional[str]] = mapped_column(
        db.String, nullable=True, default=None
    )
    latitude: Mapped[Optional[float]] = mapped_column(
        db.Float, nullable=True, default=None
    )
    longitude: Mapped[Optional[float]] = mapped_column(
        db.Float, nullable=True, default=None
    )


class Ride(Base):
    __tablename__ = "ride"
    __allow_unmapped__ = True

    id: Mapped[int] = mapped_column(
        db.Integer, primary_key=True, autoincrement=True, init=False
    )
    ride_date: Mapped[date] = mapped_column(db.Date(), nullable=False)
    start_time: Mapped[time] = mapped_column(db.Time(), nullable=False)
    total_duration: Mapped[timedelta] = mapped_column(db.Interval, nullable=False)
    distance: Mapped[float] = mapped_column(db.Float, nullable=False)

    id_bike: Mapped[Optional[int]] = mapped_column(
        db.Integer, db.ForeignKey("bike.id"), nullable=True, init=False
    )
    bike: Mapped[Bike] = relationship("Bike", backref="ride")

    id_terrain_type: Mapped[int] = mapped_column(
        db.Integer, db.ForeignKey("terrain_type.id"), nullable=False, init=False
    )
    terrain_type: Mapped[TerrainType] = relationship(
        "TerrainType", backref="ride", lazy=False
    )

    ride_duration: Mapped[Optional[timedelta]] = mapped_column(
        db.Interval, nullable=True, default=None
    )
    tracks: Mapped[list[DatabaseTrack]] = relationship(
        "DatabaseTrack",
        backref="ride",
        secondary=ride_track,
        lazy=False,
        order_by="DatabaseTrack.added",
        default_factory=lambda: [],
    )
    notes: Mapped[list[RideNote]] = relationship(
        "RideNote",
        secondary=ride_note,
        backref="ride",
        lazy=True,
        default_factory=lambda: [],
    )
    events: Mapped[list[DatabaseEvent]] = relationship(
        "DatabaseEvent",
        secondary=ride_event,
        backref="ride",
        lazy=True,
        default_factory=lambda: [],
    )

    def get_latest_track(self) -> None | DatabaseTrack:
        if not self.tracks:
            return None

        sorted_tracks = sorted(self.tracks, key=lambda t: t.added, reverse=True)
        return sorted_tracks[0]

    # TODO: Need some caching here
    @property
    def track(self) -> None | Track:
        latest_track = self.get_latest_track()
        if not latest_track:
            return None

        return ByteTrack(latest_track.content)

    @property
    def track_overview(self) -> None | TrackOverview:
        latest_track = self.get_latest_track()
        if not latest_track:
            return None

        overviews = latest_track.overviews
        for overview in overviews:
            if overview.id_segment is None:
                return overview

        raise RuntimeError("No overview for full track available")

    @property
    def track_overviews(
        self,
    ) -> tuple[None | TrackOverview, None | list[TrackOverview]]:
        latest_track = self.get_latest_track()
        if not latest_track:
            return None, None

        overviews = latest_track.overviews
        fill_overview = None
        segment_overviews = []
        for overview in overviews:
            if overview.id_segment is None:
                fill_overview = overview
            else:
                segment_overviews.append(overview)

        segment_overviews = sorted(segment_overviews, key=lambda o: o.id_segment)

        if fill_overview is None:
            raise RuntimeError("No overview for full track available")

        return fill_overview, None if len(segment_overviews) == 0 else segment_overviews

    @property
    def database_track(self) -> None | DatabaseTrack:
        return self.get_latest_track()


class DatabaseGoal(Base):
    __tablename__: str = "goal"

    id: Mapped[int] = mapped_column(db.Integer, primary_key=True, init=False)
    year: Mapped[int] = mapped_column(db.Integer, nullable=False)
    month: Mapped[Optional[int]] = mapped_column(db.Integer, nullable=True)
    name: Mapped[str] = mapped_column(db.String, nullable=False)
    goal_type: Mapped[str] = mapped_column(db.String, nullable=False)
    aggregation_type: Mapped[str] = mapped_column(db.String, nullable=False)
    threshold: Mapped[float] = mapped_column(db.Float, nullable=False)
    is_upper_bound: Mapped[bool] = mapped_column(db.Boolean, nullable=False)
    value: Mapped[Optional[float]] = mapped_column(db.Float, default=None)
    constraints: Mapped[Optional[dict]] = mapped_column(db.JSON, default=None)
    description: Mapped[Optional[str]] = mapped_column(db.TEXT, default=None)
    reached: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=False)
    active: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=True)


class DatabaseSegment(Base):
    __tablename__: str = "segment"

    id: Mapped[int] = mapped_column(
        db.Integer, primary_key=True, autoincrement=True, init=False
    )
    name: Mapped[str] = mapped_column(db.String(50), nullable=False)

    id_segment_type: Mapped[int] = mapped_column(
        db.Integer, db.ForeignKey("segment_type.id"), nullable=False, init=False
    )
    segment_type: Mapped[SegmentType] = relationship(
        "SegmentType", backref="segment", lazy=False
    )

    id_difficulty: Mapped[int] = mapped_column(
        db.Integer, db.ForeignKey("difficulty.id"), nullable=False, init=False
    )
    difficulty: Mapped[Difficulty] = relationship(
        "Difficulty", backref="segment", lazy=False
    )

    distance: Mapped[float] = mapped_column(db.Float, nullable=False)
    bounds_min_lat: Mapped[float] = mapped_column(db.Float, nullable=False)
    bounds_max_lat: Mapped[float] = mapped_column(db.Float, nullable=False)
    bounds_min_lng: Mapped[float] = mapped_column(db.Float, nullable=False)
    bounds_max_lng: Mapped[float] = mapped_column(db.Float, nullable=False)
    gpx: Mapped[bytes] = mapped_column(db.LargeBinary, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(db.TEXT, default=None)
    visited: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=False)
    min_elevation: Mapped[Optional[float]] = mapped_column(db.Float, default=None)
    max_elevation: Mapped[Optional[float]] = mapped_column(db.Float, default=None)
    uphill_elevation: Mapped[Optional[float]] = mapped_column(db.Float, default=None)
    downhill_elevation: Mapped[Optional[float]] = mapped_column(db.Float, default=None)


class DatabaseLocation(Base):
    __tablename__: str = "location"

    id: Mapped[int] = mapped_column(
        db.Integer, primary_key=True, autoincrement=True, init=False
    )
    latitude: Mapped[float] = mapped_column(db.Float, nullable=False)
    longitude: Mapped[float] = mapped_column(db.Float, nullable=False)
    name: Mapped[str] = mapped_column(db.String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(db.TEXT, default=None)

    tracks: Mapped[list[DatabaseTrack]] = relationship(
        "DatabaseTrack",
        secondary=location_track,
        backref="location",
        lazy=True,
        default_factory=lambda: [],
    )


# @dataclass
# class TrackThumbnail(Base):
#     __tablename__: str = "track_thumbnails"

#     id: int = db.Column(db.Integer, primary_key=True, autoincrement=True)
#     id_track: int = db.Column(db.Integer, db.ForeignKey("track.id"), nullable=False)
#     content: bytes = db.Column(db.LargeBinary)
