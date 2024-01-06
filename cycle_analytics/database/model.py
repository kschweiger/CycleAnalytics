from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from flask_sqlalchemy import SQLAlchemy
from geo_track_analyzer import ByteTrack, Track

db = SQLAlchemy()

ride_event = db.Table(
    "rel_ride_event",
    db.Column("ride_id", db.Integer, db.ForeignKey("ride.id")),
    db.Column("event_id", db.Integer, db.ForeignKey("event.id")),
)

ride_track = db.Table(
    "rel_ride_track",
    db.Column("ride_id", db.Integer, db.ForeignKey("ride.id")),
    db.Column("track_id", db.Integer, db.ForeignKey("track.id")),
)

ride_note = db.Table(
    "rel_ride_note",
    db.Column("ride_id", db.Integer, db.ForeignKey("ride.id")),
    db.Column("note_id", db.Integer, db.ForeignKey("ride_note.id")),
)


@dataclass
class CategoryModel(db.Model):
    __abstract__ = True

    text: str = db.Column(db.String, unique=True, nullable=False, name="text")

    def __str__(self) -> str:
        return self.text


@dataclass
class TerrainType(CategoryModel):
    id: int = db.Column(db.Integer, primary_key=True, autoincrement=True)


@dataclass
class TypeSpecification(CategoryModel):
    id: int = db.Column(db.Integer, primary_key=True, autoincrement=True)


@dataclass
class Material(CategoryModel):
    id: int = db.Column(db.Integer, primary_key=True, autoincrement=True)


@dataclass
class EventType(CategoryModel):
    id: int = db.Column(db.Integer, primary_key=True, autoincrement=True)


@dataclass
class Severity(CategoryModel):
    id: int = db.Column(db.Integer, primary_key=True, autoincrement=True)


@dataclass
class SegmentType(CategoryModel):
    id: int = db.Column(db.Integer, primary_key=True, autoincrement=True)


@dataclass
class Difficulty(CategoryModel):
    id: int = db.Column(db.Integer, primary_key=True, autoincrement=True)


@dataclass
class RideNote(db.Model):
    id: int = db.Column(db.Integer, primary_key=True)
    text: str = db.Column(db.TEXT, nullable=False)


@dataclass
class TrackOverview(db.Model):
    __table_args__ = (db.UniqueConstraint("id_track", "id_segment"),)

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_track: int = db.Column(db.Integer, db.ForeignKey("track.id"), nullable=False)
    id_segment: None | int = db.Column(db.Integer, nullable=True)
    moving_time_seconds: float = db.Column(db.Float, nullable=False)
    total_time_seconds: float = db.Column(db.Float, nullable=False)
    moving_distance: float = db.Column(db.Float, nullable=False)
    total_distance: float = db.Column(db.Float, nullable=False)
    max_velocity: float = db.Column(db.Float, nullable=False)
    avg_velocity: float = db.Column(db.Float, nullable=False)
    max_elevation: None | float = db.Column(db.Float, nullable=True)
    min_elevation: None | float = db.Column(db.Float, nullable=True)
    uphill_elevation: None | float = db.Column(db.Float, nullable=True)
    downhill_elevation: None | float = db.Column(db.Float, nullable=True)
    moving_distance_km: float = db.Column(db.Float, nullable=False)
    total_distance_km: float = db.Column(db.Float, nullable=False)
    max_velocity_kmh: float = db.Column(db.Float, nullable=False)
    avg_velocity_kmh: float = db.Column(db.Float, nullable=False)
    bounds_min_lat: float = db.Column(db.Float, nullable=False)
    bounds_max_lat: float = db.Column(db.Float, nullable=False)
    bounds_min_lng: float = db.Column(db.Float, nullable=False)
    bounds_max_lng: float = db.Column(db.Float, nullable=False)


@dataclass
class DatabaseTrack(db.Model):
    __tablename__: str = "track"
    __allow_unmapped__ = True

    id: int = db.Column(db.Integer, primary_key=True)
    content: bytes = db.Column(db.LargeBinary)
    added: datetime = db.Column(db.DateTime(timezone=True))
    is_enhanced: bool = db.Column(db.Boolean, nullable=False, default=False)

    overviews: list[TrackOverview] = db.relationship(
        "TrackOverview", backref="ride", lazy=False, cascade="all, delete"
    )  # type: ignore

    def __repr__(self) -> str:
        return (
            f"DatabaseTrack(id={self.id}, added={self.added.isoformat()}, "
            f"is_enhanced={self.is_enhanced}, content={len(self.content)} elems, "
            f"n_overviews={len(self.overviews)})"
        )


@dataclass
class Bike(db.Model):
    id: int = db.Column(db.Integer, primary_key=True)
    name: str = db.Column(db.String, unique=True, nullable=False)
    brand: str = db.Column(db.String, nullable=False)
    model: str = db.Column(db.String, nullable=False)
    id_material: int = db.Column(
        db.Integer, db.ForeignKey("material.id"), nullable=False
    )
    id_terraintype: int = db.Column(
        db.Integer, db.ForeignKey("terrain_type.id"), nullable=False
    )
    id_specification: int = db.Column(
        db.Integer, db.ForeignKey("type_specification.id"), nullable=False
    )
    weight: None | float = db.Column(db.Float)
    commission_date: date = db.Column(db.Date())
    decommission_date: None | date = db.Column(db.Date(), default=None)

    material = db.relationship("Material", backref="bike", lazy=False)
    terrain_type = db.relationship("TerrainType", backref="bike", lazy=False)
    specification = db.relationship("TypeSpecification", backref="bike", lazy=False)


@dataclass
class DatabaseEvent(db.Model):
    __tablename__: str = "event"

    id: int = db.Column(db.Integer, primary_key=True)
    event_date: date = db.Column(db.Date())
    id_event_type: int = db.Column(
        db.Integer, db.ForeignKey("event_type.id"), nullable=False
    )
    short_description: str = db.Column(db.String, nullable=False)
    description: None | str = db.Column(db.String, nullable=True)
    id_severity: None | int = db.Column(
        db.Integer, db.ForeignKey("severity.id"), nullable=True
    )
    latitude: None | float = db.Column(db.Float, nullable=True)
    longitude: None | float = db.Column(db.Float, nullable=True)
    id_bike: None | int = db.Column(db.Integer, db.ForeignKey("bike.id"), nullable=True)

    event_type = db.relationship("EventType", backref="event", lazy=False)
    severity = db.relationship("Severity", backref="event", lazy=False)
    bike = db.relationship("Bike", backref="event", lazy=True)


@dataclass
class Ride(db.Model):
    __allow_unmapped__ = True

    id: int = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ride_date: date = db.Column(db.Date(), nullable=False)
    start_time: time = db.Column(db.Time(), nullable=False)
    ride_duration: None | timedelta = db.Column(db.Interval, nullable=True)
    total_duration: timedelta = db.Column(db.Interval, nullable=False)
    distance: float = db.Column(db.Float, nullable=False)
    id_bike: None | int = db.Column(db.Integer, db.ForeignKey("bike.id"), nullable=True)
    id_terrain_type: int = db.Column(
        db.Integer, db.ForeignKey("terrain_type.id"), nullable=False
    )
    bike: Bike = db.relationship("Bike", backref="ride", lazy=True)  # type: ignore
    terrain_type: TerrainType = db.relationship(
        "TerrainType", backref="ride", lazy=False
    )  # type: ignore

    tracks: list[DatabaseTrack] = db.relationship(
        "DatabaseTrack", backref="ride", secondary=ride_track, lazy=False
    )  # type: ignore
    notes: list[RideNote] = db.relationship(
        "RideNote", secondary=ride_note, backref="ride", lazy=True
    )  # type: ignore
    events: list[DatabaseEvent] = db.relationship(
        "DatabaseEvent", secondary=ride_event, backref="ride", lazy=True
    )  # type: ignore

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

        # TODO: Other error
        raise RuntimeError("No overview for full track available")

    @property
    def database_track(self) -> None | DatabaseTrack:
        return self.get_latest_track()


@dataclass
class DatabaseGoal(db.Model):
    __tablename__: str = "goal"

    id: int = db.Column(db.Integer, primary_key=True)
    year: int = db.Column(db.Integer, nullable=False)
    month: None | int = db.Column(db.Integer, nullable=True)
    name: str = db.Column(db.String, nullable=False)
    goal_type: str = db.Column(db.String, nullable=False)
    threshold: float = db.Column(db.Float, nullable=False)
    is_upper_bound: bool = db.Column(db.Boolean, nullable=False)
    constraints: None | dict = db.Column(db.JSON)
    description: None | str = db.Column(db.TEXT)
    has_been_reached: bool = db.Column(db.Boolean, nullable=False, default=False)
    active: bool = db.Column(db.Boolean, nullable=False, default=True)


@dataclass
class DatabaseSegment(db.Model):
    __tablename__: str = "segment"

    id: int = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name: str = db.Column(db.String(50), nullable=False)
    description: None | str = db.Column(db.TEXT)
    id_segment_type: int = db.Column(
        db.Integer, db.ForeignKey("segment_type.id"), nullable=False
    )
    id_difficulty: int = db.Column(
        db.Integer, db.ForeignKey("difficulty.id"), nullable=False
    )
    distance: float = db.Column(db.Float, nullable=False)
    min_elevation: None | float = db.Column(db.Float, default=None)
    max_elevation: None | float = db.Column(db.Float, default=None)
    uphill_elevation: None | float = db.Column(db.Float, default=None)
    downhill_elevation: None | float = db.Column(db.Float, default=None)
    bounds_min_lat: float = db.Column(db.Float, nullable=False)
    bounds_max_lat: float = db.Column(db.Float, nullable=False)
    bounds_min_lng: float = db.Column(db.Float, nullable=False)
    bounds_max_lng: float = db.Column(db.Float, nullable=False)
    gpx: bytes = db.Column(db.LargeBinary, nullable=False)
    visited: bool = db.Column(db.Boolean, nullable=False, default=False)

    segment_type = db.relationship("SegmentType", backref="segment", lazy=False)
    difficulty = db.relationship("Difficulty", backref="segment", lazy=False)


def fill_data(database: SQLAlchemy) -> None:
    bike = Bike(
        name="Bike1",
        brand="Brand1",
        model="Model1",
        # material=Material(text="Aluminium"),
        id_material=1,
        id_terraintype=1,
        id_specification=1,
        commission_date=datetime.now(),
    )
    database.session.add(bike)

    ride_1 = Ride(
        ride_date=date(2023, 12, 10),
        start_time=time(12),
        total_duration=timedelta(seconds=60 * 60),
        id_terrain_type=1,
    )
    ride_2 = Ride(
        ride_date=date(2023, 12, 20),
        start_time=time(14, 30),
        ride_duration=timedelta(seconds=60 * 60 * 2),
        total_duration=timedelta(seconds=60 * 60 * 2 + 120),
        id_bike=1,
        id_terrain_type=1,
        # bike=bike,
    )
    database.session.add_all([ride_1, ride_2])
    database.session.commit()

    event_1 = DatabaseEvent(
        # ride=[ride_2],
        event_date=datetime(2023, 12, 20, 12, 15),
        id_event_type=1,
        short_description="Short description of event 1",
    )
    event_2 = DatabaseEvent(
        # ride=[ride_2],
        bike=bike,
        event_date=datetime(2023, 12, 20, 12, 50),
        id_event_type=2,
        short_description="Short description of event 2",
        description="Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed "
        "diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam",
        id_severity=1,
        latitude=10,
        longitude=10,
    )

    note = RideNote(
        text="Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam",
    )
    ride_2.events.extend([event_1, event_2])
    ride_2.notes.append(note)
    # database.session.add_all([note, event_1, event_2])

    database.session.commit()
