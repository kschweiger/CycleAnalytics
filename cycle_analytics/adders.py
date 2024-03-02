import logging
from datetime import date
from typing import Sequence

# from data_organizer.db.exceptions import QueryReturnedNoData
from flask import Blueprint, current_app, flash, redirect, render_template, request
from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from sqlalchemy.exc import IntegrityError
from werkzeug import Response
from wtforms import (
    DateField,
    DecimalField,
    HiddenField,
    IntegerField,
    RadioField,
    SelectField,
    SelectMultipleField,
    StringField,
    TextAreaField,
    TimeField,
)
from wtforms.validators import DataRequired, NumberRange, Optional

from cycle_analytics.database.model import (
    Bike,
    DatabaseEvent,
    DatabaseGoal,
    DatabaseLocation,
    EventType,
    Material,
    Ride,
    Severity,
    TerrainType,
    TypeSpecification,
)
from cycle_analytics.database.model import db as orm_db
from cycle_analytics.database.retriever import (
    get_unique_model_objects_in_db,
)
from cycle_analytics.model.base import MapData, MapPathData
from cycle_analytics.model.goal import (
    AggregationType,
    GoalType,
    is_acceptable_aggregation,
)
from cycle_analytics.utils import get_month_mapping
from cycle_analytics.utils.base import unwrap
from cycle_analytics.utils.forms import flash_form_error, get_track_from_form
from cycle_analytics.utils.track import init_db_track_and_enhance

logger = logging.getLogger(__name__)


bp = Blueprint("adders", __name__, url_prefix="/add")


class RideForm(FlaskForm):
    date = DateField("Date", validators=[DataRequired()])
    start_time = TimeField("Start Time", validators=[DataRequired()], format="%H:%M:%S")
    total_time = TimeField("Total Time", validators=[DataRequired()], format="%H:%M:%S")
    ride_time = TimeField("Ride Time", validators=[Optional()], format="%H:%M:%S")
    distance = DecimalField("Distance [km]", validators=[DataRequired()])
    bike = SelectField("Bike", validators=[DataRequired()])
    ride_type = SelectField("Ride Type")
    track = FileField("GPX Track")
    enhance_elevation = RadioField(
        "Enhance Elevation",
        choices=[(True, "Enhance Elevation")],
        coerce=bool,
        validate_choice=False,
    )


class EventForm(FlaskForm):
    date = DateField("Date", validators=[DataRequired()])
    event_type = SelectField("Type of event")
    short_description = StringField("Short description", validators=[DataRequired()])
    description = TextAreaField(
        "Description",
        default=None,
        description="Optional details on the event",
    )
    severity = SelectField(
        "Severity",
        validators=[DataRequired()],
    )
    latitude = DecimalField(
        "Latitude of event",
        description="Optional position",
        default=None,
        validators=[Optional()],
    )
    longitude = DecimalField(
        "Longitude of event",
        description="Optional position",
        default=None,
        validators=[Optional()],
    )
    id_ride = HiddenField("id_ride", default=None)
    bike = SelectField(
        "Bike Name",
        validators=[Optional()],
    )


class GoalBaseForm(FlaskForm):
    year = IntegerField(
        "Year",
        validators=[DataRequired(), NumberRange(2020, 2099)],
        default=date.today().year,
    )
    month = SelectField(
        "Month",
        validators=[DataRequired()],
    )
    multi_month_explicit = RadioField(
        "Mutli-month Settings",
        choices=[(True, "Explicit")],
        coerce=bool,
        validate_choice=False,
    )
    name = StringField(
        "Name", validators=[DataRequired()], description="Short name for the goal"
    )
    threshold = DecimalField("Threshold", validators=[DataRequired()])
    boundary = SelectField(
        "Boundary", validators=[DataRequired()], choices=[(1, "Upper"), (0, "Lower")]
    )
    description = TextAreaField(
        "Description",
        default=None,
        description="Optional longer description of the goal",
    )


class RideGoalForm(GoalBaseForm):
    month = SelectField(
        "Month",
        validators=[DataRequired()],
        choices=[(-1, "-"), (0, "All"), (-2, "Upcoming")]
        + [(i, get_month_mapping()[i]) for i in range(1, 13)],
    )
    aggregation_type = SelectField(
        "Type",
        validators=[DataRequired()],
        choices=[
            (g.value, g.description)
            for g in AggregationType
            if is_acceptable_aggregation(GoalType.RIDE, g)
        ],
    )
    ride_types = SelectMultipleField(
        "Ride Types",
        default=None,
        description="Select zero, one, or more ride types for the goal "
        "(hold ctrl or cmd to select)",
    )
    bike = SelectMultipleField(
        "Bike Name",
        default=None,
        description="Select zero, one, or more bikes for the goal "
        "(hold ctrl or cmd to select)",
    )


class ManualGoalForm(GoalBaseForm):
    month = SelectField(
        "Month",
        validators=[DataRequired()],
        choices=[(-1, "-"), (-2, "Upcoming")]
        + [(i, get_month_mapping()[i]) for i in range(1, 13)],
    )

    aggregation_type = SelectField(
        "Type",
        validators=[DataRequired()],
        choices=[
            (g.value, g.description)
            for g in AggregationType
            if is_acceptable_aggregation(GoalType.MANUAL, g)
        ],
    )


class BikeForm(FlaskForm):
    name = StringField(
        "Name",
        validators=[DataRequired()],
        description="Unique identifier for the bike",
    )
    brand = StringField(
        "Brand", validators=[DataRequired()], description="Brand of the bike"
    )
    model = StringField(
        "Model", validators=[DataRequired()], description="Full name of the bike"
    )
    material = SelectField(
        "Frame material",
        validators=[DataRequired()],
        description="Material of the frame",
    )
    weight = DecimalField(
        "Weight",
        description="Optional weight of the bike in kg",
        default=None,
        validators=[Optional()],
    )

    bike_type = SelectField(
        "Bike Type",
    )
    bike_type_specification = SelectField(
        "Type specification",
        description="Optional specification of the bike type",
        validators=[DataRequired()],
    )

    purchase = DateField("Purchase Date", validators=[DataRequired()])


class LocationForm(FlaskForm):
    name = StringField(
        "Name",
        validators=[DataRequired()],
        description="Unique identifier for the bike",
    )
    description = TextAreaField(
        "Description",
        default=None,
        description="Optional details on the event",
    )
    latitude = DecimalField(
        "Latitude of event",
        description="Optional position",
        default=None,
        validators=[Optional()],
    )
    longitude = DecimalField(
        "Longitude of event",
        description="Optional position",
        default=None,
        validators=[Optional()],
    )


@bp.route("/ride", methods=("GET", "POST"))
def add_ride() -> str | Response:
    form = RideForm()
    config = current_app.config

    all_terrain_choices = get_unique_model_objects_in_db(TerrainType)
    form.ride_type.choices = [
        (tt.id, tt.text)
        for tt in all_terrain_choices
        if tt.text == config.defaults.ride_type
    ] + [
        (tt.id, tt.text)
        for tt in all_terrain_choices
        if tt.text != config.defaults.ride_type
    ]  # type: ignore
    form.bike.choices = [(b.id, b.name) for b in get_unique_model_objects_in_db(Bike)]

    if form.validate_on_submit():
        ride = Ride(
            ride_date=unwrap(form.date.data),
            start_time=unwrap(form.start_time.data),
            ride_duration=form.ride_time.data,  # type: ignore
            total_duration=unwrap(form.total_time.data),  # type: ignore
            distance=float(unwrap(form.distance.data)),
            bike=unwrap(orm_db.session.get(Bike, int(form.bike.data))),
            terrain_type=unwrap(
                orm_db.session.get(TerrainType, int(form.ride_type.data))
            ),
        )

        orm_db.session.add(ride)
        try:
            orm_db.session.commit()
        except IntegrityError as e:
            flash("Error: %s" % e, "alert-danger")
            insert_succ = False
        else:
            flash("Ride Added", "alert-success")
            insert_succ = True

        if form.track.data is not None and insert_succ:
            try:
                track = get_track_from_form(form, "track")
            except RuntimeError as e:
                flash("Error: %s" % e, "alert-danger")
            else:
                tracks_to_insert = init_db_track_and_enhance(
                    track=track,
                    # NOTE: If enhance_elevation is switched of the track should be
                    # NOTE: considered as already enhanced
                    is_enhanced=form.enhance_elevation.data is None,
                )
                ride.tracks.extend(tracks_to_insert)
                try:
                    orm_db.session.commit()
                except IntegrityError as e:
                    flash("Error: %s" % e, "alert-danger")
                else:
                    flash(f"{len(tracks_to_insert)} tracks added", "alert-success")

        return redirect("/overview")

    elif request.method == "POST":
        flash_form_error(form)

    form.enhance_elevation.data = True

    return render_template("adders/ride.html", active_page="add_ride", form=form)


# TODO: Bike can also be be passed
@bp.route("/event", methods=("GET", "POST"))
def add_event() -> str | Response:
    config = current_app.config
    arg_date = request.args.get("date")
    arg_ride_id = request.args.get("id_ride")

    form = EventForm()

    all_event_times: Sequence[EventType] = get_unique_model_objects_in_db(EventType)
    type_choices = [
        et for et in all_event_times if et.text == config.defaults.event_type
    ] + [et for et in all_event_times if et.text != config.defaults.event_type]
    form.event_type.choices = [(c.id, c.text) for c in type_choices]
    form.id_ride.data = None
    form.bike.choices = [(-1, "-")] + [
        (b.id, b.name) for b in get_unique_model_objects_in_db(Bike)
    ]

    form.severity.choices = [(-1, "None")] + [
        (s.id, s.text) for s in get_unique_model_objects_in_db(Severity)
    ]

    if arg_date is not None:
        try:
            date.fromisoformat(arg_date)
        except ValueError as e:
            logger.error(str(e))
            flash("Date passed via the url arg is invalid", "alert-danger")
        else:
            form.date.data = date.fromisoformat(arg_date)

    map_data = None
    if arg_ride_id is not None:
        form.id_ride.data = arg_ride_id
        ride = orm_db.get_or_404(Ride, form.id_ride.data)
        track = ride.track
        if track:
            track_segment_data = track.get_track_data()
            lats = track_segment_data[track_segment_data.moving].latitude.to_list()
            lats = ",".join([str(l) for l in lats])  # noqa: E741
            longs = track_segment_data[track_segment_data.moving].longitude.to_list()
            longs = ",".join([str(l) for l in longs])  # noqa: E741

            map_data = MapData(paths=[MapPathData(latitudes=lats, longitudes=longs)])
        else:
            map_data = None

    if form.validate_on_submit():
        event = DatabaseEvent(
            event_date=unwrap(form.date.data),
            event_type=unwrap(orm_db.session.get(EventType, int(form.event_type.data))),
            severity=None
            if form.severity.data == "-1"
            else orm_db.session.get(Severity, int(form.severity.data)),
            bike=None
            if form.bike.data == "-1"
            else orm_db.session.get(Bike, int(form.bike.data)),
            short_description=unwrap(form.short_description.data),
            description=None if form.description.data == "" else form.description.data,
            latitude=form.latitude.data,  # type: ignore
            longitude=form.longitude.data,  # type: ignore
        )
        if form.id_ride.data:
            ride = orm_db.get_or_404(Ride, form.id_ride.data)
            ride.events.append(event)

        orm_db.session.add(event)
        try:
            orm_db.session.commit()
        except IntegrityError as e:
            flash("Error: %s" % e, "alert-danger")
        else:
            flash("Event Added", "alert-success")

    elif request.method == "POST":
        flash_form_error(form)

    return render_template(
        "adders/event.html",
        active_page="add_event",
        form=form,
        init_map_view=(
            config.adders.event.init_map_view_lat,
            config.adders.event.init_map_view_long,
            config.adders.event.init_map_zoom,
        ),
        map_data=map_data,
    )


@bp.route("/goal", methods=("GET", "POST"))
def add_goal() -> str | Response:
    return render_template("adders/goal_selection.html", active_page="add_goal")


def add_goal_by_type(type: GoalType) -> RideGoalForm | ManualGoalForm:
    if type == GoalType.RIDE:
        form = RideGoalForm()
        form.ride_types.choices = [
            (tt.text, tt.text) for tt in get_unique_model_objects_in_db(TerrainType)
        ]
        form.bike.choices = [
            (b.name, b.name) for b in get_unique_model_objects_in_db(Bike)
        ]
    elif type == GoalType.MANUAL:
        form = ManualGoalForm()
    else:
        raise NotImplementedError

    if form.validate_on_submit():
        constraints = {}
        if isinstance(form, (RideGoalForm)):
            if form.bike.data:
                constraints["bike"] = form.bike.data
            if form.ride_types.data:
                constraints["ride_type"] = form.ride_types.data
        if not constraints:
            constraints = None
        if form.month.data not in [None] + list(
            map(str, [-1, -2, 0] + list(range(1, 13)))
        ):
            flash(f"Invalid month value {form.month.data}", "alert-danger")
        else:
            month_values: list[None | int] = []
            # Yearly goal
            if form.month.data == "-1":
                month_values = [None]
            # Current and future month
            elif form.month.data == "-2":
                month_values = list(range(date.today().month, 13))
            # All month
            elif form.month.data == "0":
                if form.multi_month_explicit.data is not None:
                    month_values = list(range(1, 13))
                else:
                    month_values = [0]
            else:
                month_values = [int(form.month.data)]

            goals = [
                DatabaseGoal(
                    year=int(unwrap(form.year.data)),
                    month=month_value,
                    name=unwrap(form.name.data),
                    goal_type=type,
                    aggregation_type=form.aggregation_type.data,
                    threshold=float(unwrap(form.threshold.data)),
                    is_upper_bound=bool(int(form.boundary.data)),
                    constraints=constraints,
                    description=None
                    if form.description.data == ""
                    else form.description.data,
                )
                for month_value in month_values
            ]
            orm_db.session.add_all(goals)
            try:
                orm_db.session.commit()
            except IntegrityError as e:
                flash("Error: %s" % e, "alert-danger")
            else:
                flash("Goal Added", "alert-success")

    return form


@bp.route("/goal/ride", methods=("GET", "POST"))
def add_goal_ride() -> str | Response:
    form = add_goal_by_type(GoalType.RIDE)

    if request.method == "POST":
        flash_form_error(form)

    return render_template(
        "adders/goal.html",
        active_page="add_goal",
        goal_type=GoalType.RIDE,
        title="Add a new ride-dependent goal",
        form=form,
    )


@bp.route("/goal/manual", methods=("GET", "POST"))
def add_goal_manual() -> str | Response:
    form = add_goal_by_type(GoalType.MANUAL)

    if request.method == "POST":
        flash_form_error(form)

    return render_template(
        "adders/goal.html",
        active_page="add_goal",
        goal_type=GoalType.MANUAL,
        title="Add a new manual goal",
        form=form,
    )


@bp.route("/bike", methods=("GET", "POST"))
def add_bike() -> str | Response:
    form = BikeForm()

    form.bike_type.choices = [
        (tt.id, tt.text) for tt in get_unique_model_objects_in_db(TerrainType)
    ]
    form.bike_type_specification.choices = [
        (sp.id, sp.text) for sp in get_unique_model_objects_in_db(TypeSpecification)
    ]
    form.material.choices = [
        (fm.id, fm.text) for fm in get_unique_model_objects_in_db(Material)
    ]

    if form.validate_on_submit():
        bike = Bike(
            name=unwrap(form.name.data),
            brand=unwrap(form.brand.data),
            model=unwrap(form.model.data),
            material=unwrap(orm_db.session.get(Material, int(form.material.data))),
            terrain_type=unwrap(
                orm_db.session.get(TerrainType, int(form.bike_type.data))
            ),
            specification=unwrap(
                orm_db.session.get(
                    TypeSpecification, int(form.bike_type_specification.data)
                )
            ),
            weight=form.weight.data,  # type: ignore
            commission_date=unwrap(form.purchase.data),
        )
        orm_db.session.add(bike)
        try:
            orm_db.session.commit()
        except IntegrityError as e:
            flash("Error: %s" % e, "alert-danger")
        else:
            flash("Bike Added", "alert-success")

    elif request.method == "POST":
        flash_form_error(form)
    return render_template("adders/bike.html", active_page="settings", form=form)


@bp.route("/location", methods=("GET", "POST"))
def add_location() -> str | Response:
    config = current_app.config

    form = LocationForm()
    print(request.form)
    if form.validate_on_submit():
        location = DatabaseLocation(
            name=unwrap(form.name.data),
            latitude=float(unwrap(form.latitude.data)),
            longitude=float(unwrap(form.longitude.data)),
            description=None if form.description.data == "" else form.description.data,
        )
        orm_db.session.add(location)
        try:
            orm_db.session.commit()
        except IntegrityError as e:
            flash("Error: %s" % e, "alert-danger")
        else:
            flash("Location added", "alert-success")
    elif request.method == "POST":
        flash_form_error(form)

    return render_template(
        "adders/location.html",
        active_page="settings",
        form=form,
        init_map_view=(
            config.adders.event.init_map_view_lat,
            config.adders.event.init_map_view_long,
            config.adders.event.init_map_zoom,
        ),
    )
