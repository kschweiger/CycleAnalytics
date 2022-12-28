from datetime import date
from flask import Blueprint, render_template

from cycle_analytics.db import get_db


bp = Blueprint("segments", __name__, url_prefix="/segments")


@bp.route("/", methods=("GET", "POST"))
def main():
    return render_template("segments.html", active_page="segments")
