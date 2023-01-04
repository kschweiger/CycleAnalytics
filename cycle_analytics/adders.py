import json
import logging
from datetime import date

from data_organizer.db.exceptions import QueryReturnedNoData
from flask import Blueprint, current_app, flash, redirect, render_template, request
from flask_wtf import FlaskForm
from flask_wtf.file import FileField
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
from cycle_analytics.queries import get_last_id, get_track_for_id
from cycle_analytics.utils import get_month_mapping

logger = logging.getLogger(__name__)

bp = Blueprint("adders", __name__, url_prefix="/add")


class RideForm(FlaskForm):
    date = DateField("Date", validators=[DataRequired()])
    start_time = TimeField("Start Time", validators=[DataRequired()], format="%H:%M:%S")
    total_time = TimeField("Total Time", validators=[DataRequired()], format="%H:%M:%S")
    ride_time = TimeField("Ride Time", validators=[], format="%H:%M:%S")
    distance = DecimalField("Distance [km]", validators=[DataRequired()])
    bike = StringField("Bike", validators=[DataRequired()])
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
    bike = StringField("Bike Name", default=None, description="Bike name")


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


@bp.route("/ride", methods=("GET", "POST"))
def add_ride():
    form = RideForm()
    config = current_app.config

    type_choices = [config.defaults.ride_type] + [
        c for c in config.adders.ride.type_choices if c != config.defaults.ride_type
    ]

    form.ride_type.choices = [(c, c) for c in type_choices]

    form.bike.data = config.defaults.bike

    if form.validate_on_submit():
        db = get_db()
        data_to_insert = [
            [
                form.date.data,
                form.start_time.data.isoformat(),  # TEMP: Fix in DataOrganizer
                form.ride_time.data.isoformat(),  # TEMP: Fix in DataOrganizer
                form.total_time.data.isoformat(),  # TEMP: Fix in DataOrganizer
                form.distance.data,
                form.bike.data,
                form.ride_type.data,
            ]
        ]
        insert_succ, err = db.insert(
            current_app.config.tables_as_settings["main"],
            data_to_insert,
        )
        if insert_succ:
            flash("Ride added successfully", "alert-success")
        else:
            flash(f"Ride could not be added: {err}", "alert-danger")
        if form.track.data is not None and insert_succ:
            gpx_value = form.track.data.stream.read()

            last_id = get_last_id(
                current_app.config.tables_as_settings["main"].name, "id_ride", True
            )

            insert_succ, err = db.insert(
                current_app.config.tables_as_settings[
                    current_app.config.defaults.raw_track_table
                ],
                [[last_id, gpx_value]],
            )

            if insert_succ:
                flash(f"Track added for ride {last_id}", "alert-success")
            else:
                flash(f"Track could not be added: {err}", "alert-danger")

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
                form.latitude.data,
                form.longitude.data,
                form.id_ride.data,
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

    if form.validate_on_submit():

        constraints_ = {}
        if form.bike.data != "":
            constraints_["bike"] = form.bike.data.split(",")
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
