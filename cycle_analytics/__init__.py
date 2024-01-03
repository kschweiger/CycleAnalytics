import logging

from dynaconf import FlaskDynaconf, Validator
from flask import Flask, request, send_file
from flask.logging import default_handler
from flask_wtf.csrf import CSRFProtect
from werkzeug import Response

from cycle_analytics.database.creator import (
    sync_categorical_values,
)
from cycle_analytics.database.model import db as orm_db
from cycle_analytics.landing_page import render_landing_page
from cycle_analytics.serve import get_segment_download, get_track_download

logger = logging.getLogger(__name__)


def create_app(
    dynaconf_kwargs: None | dict = None, test_config: None | dict = None
) -> Flask:
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)

    for logger_ in (
        app.logger,
        logging.getLogger("track_analyzer"),
        logging.getLogger("data_organizer"),
    ):
        logger_.setLevel("DEBUG" if app.debug else "INFO")
        logger_.addHandler(default_handler)

    if dynaconf_kwargs is None:
        dynaconf_kwargs = {}

    logger.debug("Initializing FlaskDynaconf")
    cfg = FlaskDynaconf(
        app=app,
        settings_files=["conf/settings.toml", "conf/.secrets.toml"],
        validators=[
            Validator("secret_key", must_exist=True),
            Validator("database_schema", default=None),
            Validator("SQLALCHEMY_ENGINE_OPTIONS", default={}),
        ],
        **dynaconf_kwargs,
    )

    logger.info("Using dynaconf environment %s", cfg.settings.env_for_dynaconf)

    if test_config is not None:
        cfg.settings.update(test_config)

    from cycle_analytics.cache import cache

    logger.debug("Initializing Cache")
    cache.init_app(app=app)

    logger.debug("Running cache: %s", type(cache.cache).__name__)

    logger.debug("Initializing CSRF protection from FLASK-WTF")
    CSRFProtect(app)

    if app.config.database_schema is not None:
        app.config.SQLALCHEMY_ENGINE_OPTIONS.update(
            {
                "connect_args": {
                    "options": f"-csearch_path={app.config.database_schema},public"
                }
            }
        )

    orm_db.init_app(app)

    if cfg.settings.EXTENSIONS:
        app.config.load_extensions()

    with app.app_context():
        orm_db.create_all()
        sync_categorical_values(orm_db)

    @app.route("/", methods=["GET", "POST"])
    def landing_page() -> str:
        return render_landing_page()

    @app.route("/download", methods=["GET"])
    def download_data() -> Response:
        data_type = request.args.get("datatype")
        if data_type in ["track", "segment"]:
            identifier = request.args.get("id")
            if identifier is None:
                raise KeyError(
                    "An id must be passed as parameter for track and segement download"
                )

            if data_type == "track":
                data, name = get_track_download(int(identifier))
            if data_type == "segment":
                data, name = get_segment_download(int(identifier))

        else:
            raise NotImplementedError(
                "Data type %s is not supported for download" % data_type
            )

        return send_file(data, download_name=name, as_attachment=True)  # type: ignore

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

    from cycle_analytics.track import bp as track

    app.register_blueprint(track)

    return app
