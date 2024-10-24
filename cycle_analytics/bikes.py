import logging

from flask import Blueprint, flash, redirect, render_template, url_for
from sqlalchemy.exc import NoResultFound
from werkzeug import Response

from .database.model import Bike
from .database.model import db as orm_db
from .database.retriever import get_agg_data_for_bike

logger = logging.getLogger(__name__)


bp = Blueprint("bike", __name__, url_prefix="/bike")


@bp.route("/<bike_name>/", methods=("GET", "POST"))
def show(bike_name: str) -> str | Response:
    try:
        bike = orm_db.session.execute(
            orm_db.select(Bike).filter_by(name=bike_name)
        ).scalar_one()

    except NoResultFound:
        flash(
            f"<b>{bike_name}</b> is no valid bike. You can add it via "
            f"<a href='{url_for('adders.add_bike')}'>this form</a>",
            "alert-danger",
        )
        return redirect("/")

    agg_data = get_agg_data_for_bike(bike.id)

    return render_template(
        "show_bike.html", active_page="bike", bike=bike, agg_data=agg_data
    )
