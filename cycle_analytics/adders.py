import json
from datetime import date

from flask import Blueprint, current_app, flash, redirect, render_template, request
from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from wtforms import (
    DateField,
    DecimalField,
    IntegerField,
    SelectField,
    SelectMultipleField,
    StringField,
    TextAreaField,
    TimeField,
)
from wtforms.validators import DataRequired, NumberRange

from cycle_analytics.db import get_db
from cycle_analytics.goals import GoalType
from cycle_analytics.queries import get_last_id
from cycle_analytics.utils import get_month_mapping

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


@bp.route("/ride", methods=("GET", "POST"))
def add_ride():
    form = RideForm()
    config = current_app.config

    type_choices = [config.defaults.ride_type] + [
        c for c in config.adders.ride.type_choices if c != config.defaults.ride_type
    ]

    form.ride_type.choices = [(c, c) for c in type_choices]

    form.bike.data = config.defaults.bike

    print(request.form)
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
        flash(
            "\n".join(
                ["<ul>"]
                + [
                    f"<li>{field} - {','.join(error)}</li>"
                    for field, error in form.errors.items()
                ]
                + ["</ul>"]
            ),
            "alert-danger",
        )

    return render_template("adders/ride.html", active_page="add_ride", form=form)


@bp.route("/event", methods=("GET", "POST"))
def add_event():
    return render_template("adders/event.html", active_page="add_event")


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
        print(data_to_insert)
        insert_succ, err = db.insert(
            current_app.config.tables_as_settings["goals"],
            data_to_insert,
        )
        if insert_succ:
            flash("Goal Added", "alert-success")
        else:
            flash(f"Track could not be added: {err}", "alert-danger")

    return render_template("adders/goal.html", active_page="add_goal", form=form)
