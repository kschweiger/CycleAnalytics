from flask import Blueprint, render_template
from flask_wtf import FlaskForm
from wtforms import DateField, TimeField, StringField, FloatField, SelectField
from flask_wtf.file import FileField
from wtforms.validators import DataRequired

from cycle_analytics.db import get_db


bp = Blueprint("adders", __name__, url_prefix="/add")


class RideForm(FlaskForm):
    date = DateField("Date", validators=[DataRequired()])
    start_time = TimeField("Start Time", validators=[DataRequired()])
    total_time = TimeField("Total Time", validators=[DataRequired()])
    ride_time = TimeField("Ride Time", validators=[])
    distance = FloatField("Distance [km]", validators=[DataRequired()])
    bike = StringField("Bike", validators=[DataRequired()])
    ride_type = SelectField("Ride Type", choices=[("mtb", "MTB"), ("road", "Road")])
    track = FileField("GPX Track")


@bp.route("/ride", methods=("GET", "POST"))
def add_ride():
    form = RideForm()

    # TEMP ---------- START ----------
    form.bike.data = "Default Bike"
    # TEMP ----------  END  ----------

    return render_template("adders/ride.html", active_page="add_ride", form=form)


@bp.route("/event", methods=("GET", "POST"))
def add_event():
    return render_template("adders/event.html", active_page="add_event")
