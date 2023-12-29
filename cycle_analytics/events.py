from datetime import date

from flask import Blueprint, current_app, flash, render_template
from flask_wtf import FlaskForm
from wtforms import SelectField
from wtforms.validators import DataRequired

from cycle_analytics.database.retriever import get_event_years_in_database, get_events
from cycle_analytics.model.base import MapMarker
from cycle_analytics.utils import get_month_mapping


class OverviewForm(FlaskForm):
    year = SelectField(
        "Year", validators=[DataRequired()], default=str(date.today().year)
    )
    month = SelectField(
        "Month",
        validators=[DataRequired()],
        choices=[(0, "All")] + [(i, get_month_mapping()[i]) for i in range(1, 13)],
        default=0,
    )
    event_type = SelectField("Event Type", validators=[DataRequired()], default="All")


bp = Blueprint("events", __name__, url_prefix="/events")


@bp.route("/", methods=("GET", "POST"))
def overview() -> str:
    config = current_app.config

    table_headings = [
        "Description",
        "Type",
        "Date",
        "Severity",
    ]

    severity_mapping = config.mappings.severity.to_dict()
    event_colors = config.mappings.event_colors.to_dict()

    avail_event_years = get_event_years_in_database()

    overview_form = OverviewForm()
    type_choices = ["All"] + config.adders.event.type_choices

    overview_form.event_type.choices = [(c, c) for c in type_choices]

    curr_year = date.today().year
    overview_form.year.choices = (
        [(str(curr_year), str(curr_year))]
        + [(str(y), str(y)) for y in avail_event_years if y != curr_year]
        + [("All", "All")]
    )

    # Format the values from the form so it can be used in the queries
    load_year = overview_form.year.data
    if load_year == "All":
        load_year = None
    else:
        load_year = int(load_year)
    load_month: None | int = int(overview_form.month.data)
    if load_month == 0:
        load_month = None
    load_type = overview_form.event_type.data
    if load_type == "All":
        load_type = None
    else:
        load_type = [load_type]

    table_data = []
    events = get_events(load_year, load_month, load_type)

    located_events = []
    if not events:
        flash("No data available considering constraints selected", "alert-warning")
    else:
        for event in events:
            table_data.append(
                (
                    event.short_description,
                    event.event_type,
                    event.event_date,
                    "" if event.id_severity is None else event.severity.text,
                )
            )
            if event.latitude is not None and event.longitude is not None:
                color = "blue"
                if event.event_type.text in event_colors.keys():
                    color = event_colors[event.event_type.text]

                popup_text = f"<b>{event.short_description}</b>"
                if event.severity is not None:
                    popup_text += f" - Severity: {event.severity.text}"
                if event.description is not None:
                    popup_text += f"<br>{event.description}"
                located_events.append(
                    MapMarker(
                        latitude=event.latitude,
                        longitude=event.longitude,
                        popup_text=popup_text,
                        color=color,
                        color_idx=0
                        if event.id_severity is None
                        else event.id_severity - 1,
                    )
                )

    return render_template(
        "events.html",
        active_page="events",
        overview_form=overview_form,
        table_data=(table_headings, table_data),
        located_events=located_events,
    )
