import json
import logging
from datetime import date

from data_organizer.db.exceptions import QueryReturnedNoData
from flask import Blueprint, current_app, flash, redirect, render_template, request
from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from gpx_track_analyzer.enhancer import get_enhancer
from gpx_track_analyzer.exceptions import (
    APIHealthCheckFailedException,
    APIResponseException,
)
from gpx_track_analyzer.track import ByteTrack, Track
from wtforms import (
    DateField,
    DecimalField,
    HiddenField,
    IntegerField,
    SelectField,
    SelectMultipleField,
    StringField,
    TextAreaField,
    TimeField,
)
from wtforms.validators import DataRequired, NumberRange, Optional

from cycle_analytics.db import get_db
from cycle_analytics.goals import GoalType
from cycle_analytics.model import MapData, MapPathData
from cycle_analytics.queries import (
    get_bike_names,
    get_last_id,
    get_last_track_id,
    get_track_for_id,
)
from cycle_analytics.utils import get_month_mapping

logger = logging.getLogger(__name__)

numeric = int | float

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
        choices=[
            (-1, "None"),
            (0, "Minor"),
            (1, "Medium"),
            (2, "Major"),
            (3, "Critical"),
        ],
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


class GoalForm(FlaskForm):
    year = IntegerField(
        "Year",
        validators=[DataRequired(), NumberRange(2022, 2099)],
        default=date.today().year,
    )
    month = SelectField(
        "Month",
        validators=[DataRequired()],
        choices=[(-1, "-"), (0, "All")]
        + [(i, get_month_mapping()[i]) for i in range(1, 13)],
    )
    name = StringField(
        "Name", validators=[DataRequired()], description="Short name for the goal"
    )
    goal_type = SelectField(
        "Type",
        validators=[DataRequired()],
        choices=[(g.value, g.description) for g in GoalType],
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
    material = StringField(
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
        choices=[("mtb", "MTB"), ("road", "Road"), ("gravel", "Gravel")],
        default="mtb",
    )
    bike_type_specification = StringField(
        "Type specification",
        description="Optional specification of the bike type",
        default=None,
        validators=[Optional()],
    )

    purchase = DateField("Purchase Date", validators=[DataRequired()])


def flash_form_error(form: FlaskForm):
    flash(
        "\n".join(
            ["<ul>"]
            + [
                f"<li>{field} - {','.join(error)} - Got **{form[field].data}**</li>"
                for field, error in form.errors.items()
            ]
            + ["</ul>"]
        ),
        "alert-danger",
    )


def enhance_track(
    track: Track,
) -> tuple[None, None] | tuple[bytes, list[list[numeric]]]:
    track_data = None
    track_overview_data = None

    enhancer = None
    try:
        enhancer = get_enhancer(current_app.config.external.track_enhancer.name)(
            url=current_app.config.external.track_enhancer.url,
            **current_app.config.external.track_enhancer.kwargs.to_dict(),
        )
    except APIHealthCheckFailedException:
        logger.warning("Enhancer not available. Skipping elevation profile")
        flash("Track could not be enhanced - API not available")
        return None, None

    try:
        enhancer.enhance_track(track.track, True)
    except APIResponseException:
        logger.error("Could not enhance track with elevation")
        return None, None

    track_data = track.get_xml().encode()

    track_overview_data = []

    for i_segment in range(track.n_segments):
        this_track_overview = track.get_segment_overview(i_segment)
        bounds = track.track.get_bounds()
        track_overview_data.append(
            [
                i_segment,
                this_track_overview.moving_time_seconds,
                this_track_overview.total_time_seconds,
                this_track_overview.moving_distance,
                this_track_overview.total_distance,
                this_track_overview.max_velocity,
                this_track_overview.avg_velocity,
                this_track_overview.max_elevation,
                this_track_overview.min_elevation,
                this_track_overview.uphill_elevation,
                this_track_overview.downhill_elevation,
                this_track_overview.moving_distance_km,
                this_track_overview.total_distance_km,
                this_track_overview.max_velocity_kmh,
                this_track_overview.avg_velocity_kmh,
                bounds.min_latitude,
                bounds.max_latitude,
                bounds.min_longitude,
                bounds.max_longitude,
            ]
        )

    return track_data, track_overview_data


@bp.route("/ride", methods=("GET", "POST"))
def add_ride():
    form = RideForm()
    config = current_app.config

    type_choices = [config.defaults.ride_type] + [
        c for c in config.adders.ride.type_choices if c != config.defaults.ride_type
    ]

    form.ride_type.choices = [(c, c) for c in type_choices]
    form.bike.choices = [(b, b) for b in get_bike_names()]

    if form.validate_on_submit():
        db = get_db()
        data_to_insert = [
            [
                form.date.data,
                form.start_time.data.isoformat(),  # TEMP: Fix in DataOrganizer
                form.ride_time.data.isoformat()
                if form.ride_time.data
                else None,  # TEMP: Fix in DataOrganizer
                form.total_time.data.isoformat(),  # TEMP: Fix in DataOrganizer
                form.distance.data,
                form.bike.data,
                form.ride_type.data,
            ]
        ]
        insert_succ, err = db.insert(
            current_app.config.tables_as_settings[
                current_app.config.defaults.main_data_table
            ],
            data_to_insert,
        )
        if insert_succ:
            flash("Ride added successfully", "alert-success")
        else:
            flash(f"Ride could not be added: {err}", "alert-danger")
        if form.track.data is not None and insert_succ:
            gpx_value = form.track.data.stream.read()

            last_id = get_last_id(
                current_app.config.tables_as_settings[
                    current_app.config.defaults.main_data_table
                ].name,
                "id_ride",
                True,
                None,
            )

            insert_succ_track, err = db.insert(
                current_app.config.tables_as_settings[
                    current_app.config.defaults.raw_track_table
                ],
                [[last_id, gpx_value]],
            )

            if insert_succ_track:
                flash(f"Track added for ride {last_id}", "alert-success")

                enhancer = None
                try:
                    enhancer = get_enhancer(config.external.track_enhancer.name)(
                        url=config.external.track_enhancer.url,
                        **config.external.track_enhancer.kwargs.to_dict(),
                    )
                except APIHealthCheckFailedException:
                    logger.warning("Enhancer not available. Skipping elevation profile")
                    flash("Track could not be enhanced - API not available")
                if enhancer is not None:
                    track = ByteTrack(gpx_value)
                    try:
                        enhancer.enhance_track(track.track, True)
                    except APIResponseException:
                        logger.error("Could not enhance track with elevation")

                    enhance_insert_succ_track, err = db.insert(
                        current_app.config.tables_as_settings[
                            current_app.config.defaults.track_table
                        ],
                        [[last_id, track.get_xml().encode()]],
                    )

                    if enhance_insert_succ_track:
                        flash(
                            f"Enhanced Track added for ride {last_id}", "alert-success"
                        )
                        new_data_to_insert = []
                        id_track = get_last_track_id(
                            current_app.config.defaults.track_table, "id_track", True
                        )
                        for i_segment in range(track.n_segments):
                            this_track_overview = track.get_segment_overview(i_segment)
                            bounds = track.track.get_bounds()
                            new_data_to_insert.append(
                                [
                                    id_track,
                                    i_segment,
                                    this_track_overview.moving_time_seconds,
                                    this_track_overview.total_time_seconds,
                                    this_track_overview.moving_distance,
                                    this_track_overview.total_distance,
                                    this_track_overview.max_velocity,
                                    this_track_overview.avg_velocity,
                                    this_track_overview.max_elevation,
                                    this_track_overview.min_elevation,
                                    this_track_overview.uphill_elevation,
                                    this_track_overview.downhill_elevation,
                                    this_track_overview.moving_distance_km,
                                    this_track_overview.total_distance_km,
                                    this_track_overview.max_velocity_kmh,
                                    this_track_overview.avg_velocity_kmh,
                                    bounds.min_latitude,
                                    bounds.max_latitude,
                                    bounds.min_longitude,
                                    bounds.max_longitude,
                                ]
                            )
                        if new_data_to_insert:
                            overview_insert_succ_track, err = db.insert(
                                current_app.config.tables_as_settings[
                                    current_app.config.defaults.track_overview_table
                                ],
                                new_data_to_insert,
                            )
                            if overview_insert_succ_track:
                                flash(
                                    f"Overview inserted for track {id_track}",
                                    "alert-success",
                                )
                            else:
                                flash(
                                    f"Overview could not be generated: {err[0:250]}",
                                    "alert-danger",
                                )
                        else:
                            logger.info("No data to insert", "alter-warning")
                    else:
                        flash(
                            f"Enhanced Track could not be inserted: {err[0:250]}",
                            "alert-danger",
                        )

            else:
                flash(f"Track could not be added: {err[0:250]}", "alert-danger")

        return redirect("/overview")

    elif request.method == "POST":
        flash_form_error(form)

    return render_template("adders/ride.html", active_page="add_ride", form=form)


@bp.route("/event", methods=("GET", "POST"))
def add_event():
    config = current_app.config
    arg_date = request.args.get("date")
    arg_ride_id = request.args.get("id_ride")

    form = EventForm()
    type_choices = [config.defaults.event_type] + [
        c for c in config.adders.event.type_choices if c != config.defaults.event_type
    ]

    form.event_type.choices = [(c, c) for c in type_choices]
    form.id_ride.data = None
    form.bike.choices = [("None", "-")] + [(b, b) for b in get_bike_names()]

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
        try:
            track = get_track_for_id(arg_ride_id)
        except QueryReturnedNoData:
            map_data = None
        else:
            track_segment_data = track.get_segment_data(0)
            lats = track_segment_data[track_segment_data.moving].latitude.to_list()
            lats = ",".join([str(l) for l in lats])  # noqa: E741
            longs = track_segment_data[track_segment_data.moving].longitude.to_list()
            longs = ",".join([str(l) for l in longs])  # noqa: E741

            map_data = MapData(path=MapPathData(latitudes=lats, longitudes=longs))

    if form.validate_on_submit():
        db = get_db()
        data_to_insert = [
            [
                form.date.data,
                form.event_type.data,
                form.short_description.data,
                None if form.description.data == "" else form.description.data,
                None if int(form.severity.data) == -1 else form.severity.data,
                form.latitude.data,
                form.longitude.data,
                form.id_ride.data,
                None if form.bike.data == "None" else form.bike.data,
            ]
        ]
        insert_succ, err = db.insert(
            current_app.config.tables_as_settings["events"],
            data_to_insert,
        )
        if insert_succ:
            flash("Event Added", "alert-success")
        else:
            flash(f"Event could not be added: {err}", "alert-danger")

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
def add_goal():
    form = GoalForm()
    config = current_app.config

    form.ride_types.choices = config.adders.ride.type_choices
    form.bike.choices = get_bike_names()

    if form.validate_on_submit():
        constraints_ = {}
        if form.bike.data:
            constraints_["bike"] = form.bike.data
        if form.ride_types.data:
            constraints_["ride_type"] = form.ride_types.data

        constraints: None | str = None
        if constraints_:
            constraints = json.dumps(constraints_)
        db = get_db()
        data_to_insert = [
            [
                form.year.data,
                None if int(form.month.data) == -1 else int(form.month.data),
                form.name.data,
                form.goal_type.data,
                form.threshold.data,
                bool(int(form.boundary.data)),
                constraints,  # Constraints
                None if form.description.data == "" else form.description.data,
                False,  # has_been_reached
                True,  # Active
            ]
        ]
        insert_succ, err = db.insert(
            current_app.config.tables_as_settings["goals"],
            data_to_insert,
        )
        if insert_succ:
            flash("Goal Added", "alert-success")
        else:
            flash(f"Track could not be added: {err}", "alert-danger")

    return render_template("adders/goal.html", active_page="add_goal", form=form)


@bp.route("/bike", methods=("GET", "POST"))
def add_bike():
    form = BikeForm()

    if form.validate_on_submit():
        data_to_insert = [
            (
                form.name.data,
                form.brand.data,
                form.model.data,
                form.material.data,
                form.bike_type.data,
                None
                if form.bike_type_specification.data == ""
                else form.bike_type_specification.data,
                form.weight.data,
                form.purchase.data.isoformat(),
                None,
            )
        ]
        db = get_db()
        insert_succ, err = db.insert(
            current_app.config.tables_as_settings["bikes"],
            data_to_insert,
        )
        if insert_succ:
            flash("Goal Added", "alert-success")
        else:
            flash(f"Track could not be added: {err}", "alert-danger")
    elif request.method == "POST":
        flash_form_error(form)
    return render_template("adders/bike.html", active_page="settings", form=form)
