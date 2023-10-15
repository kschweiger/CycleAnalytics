import logging

from flask import Blueprint, flash, render_template, request

from cycle_analytics.cache import cache

logger = logging.getLogger(__name__)

bp = Blueprint("settings", __name__, url_prefix="/settings")


@bp.route("/", methods=("GET", "POST"))
def main() -> str:
    if request.method == "POST":
        if request.form.get("reset_cache") is not None:
            logger.warning("Resetting cache")
            cache.clear()
            flash("Cache cleared", "alert-warning")

    return render_template(
        "settings.html",
        active_page="settings",
    )
