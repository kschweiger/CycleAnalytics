import logging
from datetime import date

from flask import current_app, render_template, request

from .database.converter import (
    convert_ride_overview_container_to_df,
    summarize_rides_in_month,
    summarize_rides_in_year,
)
from .database.retriever import (
    get_goal_years_in_database,
    get_last_ride,
    get_recent_events,
    get_ride_and_latest_track_overview,
    get_ride_years_in_database,
    load_goals,
    resolve_track_location_association,
)
from .forms import YearAndRideTypeForm
from .model.goal import (
    LocationGoal,
    ManualGoal,
    RideGoal,
    format_goals_concise,
)
from .utils import get_month_mapping
from .utils.base import get_curr_and_prev_month_date_ranges, unwrap

logger = logging.getLogger(__name__)


def render_landing_page() -> str:
    logger.debug("Rendering landing page")
    config = current_app.config
    date_today = date.today()

    # --------------------- LAST RIDES ---------------------
    last_ride_types = ["Any"] + config.adders.ride.type_choices
    last_ride_type_selected = config.landing_page.last_ride.default_type
    if request.method == "POST" and request.form.get("form_last_ride_type") is not None:
        last_ride_type_selected = request.form.get("form_last_ride_type")

    last_ride = get_last_ride(
        None if last_ride_type_selected == "Any" else last_ride_type_selected
    )
    logger.info("Last ride done")
    # --------------------- RECENT EVENTS ---------------------
    recent_event_type_selected = "All"
    recent_event_types = ["All"] + config.adders.event.type_choices
    if (
        request.method == "POST"
        and request.form.get("form_recent_event_type") is not None
    ):
        recent_event_type_selected = request.form.get("form_recent_event_type")

    events = get_recent_events(
        config.landing_page.events.n_max_recent,
        None if recent_event_type_selected == "All" else recent_event_type_selected,
    )

    recent_events = []

    for event in events:
        recent_events.append(
            (
                event.short_description,
                event.event_type,
                event.event_date,
            )
        )
    logger.info("Recent events done")
    # --------------------- GOALS ---------------------
    goal_years = [
        str(g)
        for g in sorted(
            set(get_goal_years_in_database() + [date_today.year]), reverse=True
        )
    ]
    month_mapping = get_month_mapping()
    goal_year_selected = str(date_today.year)
    goal_month_selected = month_mapping[date_today.month]

    if request.method == "POST" and request.form.get("form_goals_year") is not None:
        goal_year_selected = unwrap(request.form.get("form_goals_year"))
        goal_month_selected = unwrap(request.form.get("form_goals_month"))

    inv_month_mapping = {value: key for key, value in month_mapping.items()}
    goal_months = [month_mapping[i] for i in range(1, 13)]

    goals_ = load_goals(goal_year_selected, True, False)

    display_goals = [
        goal
        for goal in goals_
        if (
            goal.month is None  # YearlyGoals
            or goal.month == inv_month_mapping[goal_month_selected]
        )
    ]
    # -----------------------------------------------------------------------------
    data = convert_ride_overview_container_to_df(
        get_ride_and_latest_track_overview(goal_year_selected)
    )
    data_locations = resolve_track_location_association(goal_year_selected)
    for goal in display_goals:
        if isinstance(goal, RideGoal):
            this_evaluation = goal.evaluate(data)
        elif isinstance(goal, ManualGoal):
            this_evaluation = goal.evaluate()
        elif isinstance(goal, LocationGoal):
            this_evaluation = goal.evaluate(data_locations)
        else:
            raise NotImplementedError
        goal.reached = this_evaluation.reached
    # -----------------------------------------------------------------------------

    goals = format_goals_concise(display_goals)
    logger.info("Goals doen")
    # --------------------- SUMMARY ---------------------
    summary_form = YearAndRideTypeForm()

    summary_form.ride_type.choices = [
        ("Default", " , ".join(config.overview.default_types)),
        ("All", "All"),
    ] + [(c, c) for c in config.adders.ride.type_choices]

    curr_year = date.today().year
    years = [curr_year] + get_ride_years_in_database()
    year_choices = map(str, ["All"] + sorted(set(years), reverse=True))
    summary_form.year.choices = [(y, y) for y in year_choices]
    summary_year_selected = summary_form.year.data
    select_ride_types_ = summary_form.ride_type.data
    if select_ride_types_ == "Default":
        summary_ride_type_selected = config.overview.default_types
    else:
        summary_ride_type_selected = select_ride_types_

    summary_data = summarize_rides_in_year(
        convert_ride_overview_container_to_df(
            get_ride_and_latest_track_overview(
                summary_year_selected, summary_ride_type_selected
            )
        )
        # get_rides_in_timeframe(summary_year_selected, summary_ride_type_selected)
    )

    summary_month = summarize_rides_in_month(
        *[
            convert_ride_overview_container_to_df(
                get_ride_and_latest_track_overview(date_range)
            )
            for date_range in get_curr_and_prev_month_date_ranges(
                date_today.year, date_today.month
            )
        ]
        # *get_curr_and_prev_month_rides(date_today.year, date_today.month)
    )

    logger.info("summary done")
    return render_template(
        "landing_page.html",
        active_page="home",
        last_ride=last_ride,
        last_ride_types=last_ride_types,
        last_ride_type_selected=last_ride_type_selected,
        recent_events=recent_events,
        recent_event_types=recent_event_types,
        recent_event_type_selected=recent_event_type_selected,
        goal_months=goal_months,
        goal_month_selected=goal_month_selected,
        goal_years=goal_years,
        goal_year_selected=goal_year_selected,
        goals=goals,
        summary_form=summary_form,
        summary_year_selected=summary_year_selected,
        summary_ride_type_selected=summary_ride_type_selected,
        summary_data=summary_data,
        summary_month=summary_month,
    )
