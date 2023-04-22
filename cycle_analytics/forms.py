from datetime import date

from flask_wtf import FlaskForm
from wtforms import SelectField
from wtforms.validators import DataRequired


class YearAndRideTypeForm(FlaskForm):
    year = SelectField(
        "Year", validators=[DataRequired()], default=str(date.today().year)
    )

    ride_type = SelectField("Ride Type", validators=[DataRequired()], default="Default")
