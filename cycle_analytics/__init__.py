import logging

from data_organizer.config import OrganizerConfig
from dynaconf import FlaskDynaconf
from flask import Flask
from flask.logging import default_handler
from flask_wtf.csrf import CSRFProtect

from cycle_analytics.landing_page import render_landing_page

logger = logging.getLogger(__name__)


def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        CACHE_TYPE="SimpleCache",
        CACHE_DEFAULT_TIMEOUT=300,
        SECRET_KEY="dev",
    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile("config.py", silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    for logger in (
        app.logger,
        logging.getLogger("gpx_track_analyzer"),
        logging.getLogger("data_organizer"),
    ):
        logger.setLevel("DEBUG" if app.debug else "INFO")
        logger.addHandler(default_handler)

    organizer_config = OrganizerConfig(
        name="CycleAnalytics",
        config_dir_base="conf/",
    )

    logger.debug("Initializing FlaskDynaconf")
    FlaskDynaconf(app=app, dynaconf_instance=organizer_config.settings)

    from cycle_analytics.cache import cache

    logger.debug("Initializing Cache")
    cache.init_app(app=app)

    logger.debug("Running cache: %s", type(cache.cache))

    from cycle_analytics import db

    logger.debug("Initializing DB")
    db.init_app(app)

    logger.debug("Initializing CSRF protection from FLASK-WTF")
    CSRFProtect(app)

    @app.route("/", methods=["GET", "POST"])
    def landing_page():
        return render_landing_page()

    from cycle_analytics.segments import bp as segments

    app.register_blueprint(segments)

    from cycle_analytics.overview import bp as overview

    app.register_blueprint(overview)

    from cycle_analytics.goals import bp as goals

    app.register_blueprint(goals)

    from cycle_analytics.events import bp as events

    app.register_blueprint(events)

    from cycle_analytics.ride import bp as ride

    app.register_blueprint(ride)

    from cycle_analytics.adders import bp as adders

    app.register_blueprint(adders)

    from cycle_analytics.bikes import bp as bikes

    app.register_blueprint(bikes)

    from cycle_analytics.settings import bp as settings

    app.register_blueprint(settings)

    return app
