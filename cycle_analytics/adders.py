from flask import Blueprint, current_app, flash, redirect, render_template, request
from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from wtforms import DateField, DecimalField, SelectField, StringField, TimeField
from wtforms.validators import DataRequired

from cycle_analytics.db import get_db
from cycle_analytics.queries import get_last_id

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
