import json
import logging
from collections import defaultdict

# from data_organizer.db.exceptions import QueryReturnedNoData
from flask import (
    Blueprint,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_wtf import FlaskForm
from geo_track_analyzer import ByteTrack
from geo_track_analyzer.enhancer import get_enhancer
from geo_track_analyzer.exceptions import (
    APIHealthCheckFailedError,
    APIResponseError,
)
from geo_track_analyzer.track import PyTrack
from plotly.utils import PlotlyJSONEncoder
from pydantic import ValidationError
from pyroutelib3 import Router
from sqlalchemy.exc import IntegrityError
from werkzeug import Response
from wtforms import HiddenField, SelectField, StringField, TextAreaField
from wtforms.validators import DataRequired, Optional

from cycle_analytics.database.model import DatabaseSegment, Difficulty, SegmentType
from cycle_analytics.database.model import db as orm_db
from cycle_analytics.database.modifier import modify_segment_visited_flag
from cycle_analytics.database.retriever import (
    get_segments_for_map_in_bounds,
    get_unique_model_objects_in_db,
)
from cycle_analytics.model.base import MapData, MapPathData
from cycle_analytics.plotting import (
    convert_fig_to_base64,
    get_track_elevation_plot,
    get_track_elevation_slope_plot,
)
from cycle_analytics.rest_models import (
    SegmentsInBoundsRequest,
    SegmentsInBoundsResponse,
)
from cycle_analytics.utils import find_closest_elem_to_poi
from cycle_analytics.utils.forms import flash_form_error

logger = logging.getLogger(__name__)

bp = Blueprint("segments", __name__, url_prefix="/segments")


class AddMapSegmentForm(FlaskForm):
    segment_latitudes = HiddenField(
        "Latitudes of the segment", validators=[DataRequired()]
    )
    segment_longitudes = HiddenField(
        "Longitudes of the segment", validators=[DataRequired()]
    )
    segment_elevations = HiddenField(
        "Elevation values of the segment", validators=[Optional()], default=None
    )
    segment_name = StringField(
        "Name of the Segment",
        validators=[DataRequired()],
        description="Name of the Segment",
    )
    segment_description = TextAreaField(
        "Description",
        description="Optional details on the event",
        validators=[Optional()],
    )
    segment_type = SelectField("Type of the segment")
    segment_difficulty = SelectField("Difficulty of the segment", default=0)


@bp.route("/", methods=("GET", "POST"))
def main() -> str | Response:
    return render_template("segments/overview.html", active_page="segments")


@bp.route("/show/<int:id_segment>", methods=("GET", "POST"))
def show_segment(id_segment: int) -> str | Response:
    if request.form.get("change_visited_flag") is not None:
        switch_to = request.form.get("change_visited_flag") == "visited"
        modify_segment_visited_flag(
            id_segment=id_segment,
            visited=switch_to,
        )
        logger.info("Switch segmenet %s to %s", id_segment, switch_to)

    segment: None | DatabaseSegment = orm_db.session.get(DatabaseSegment, id_segment)
    if segment is None:
        flash(
            "Invalid value of id_segnebt. Redirecting to main segment view",
            "alert-danger",
        )
        return redirect(url_for("segments.main"))

    segment_track = ByteTrack(segment.gpx, 0)

    track_segment_data = segment_track.get_segment_data(0)

    lats = track_segment_data[track_segment_data.moving].latitude.to_list()
    lats = ",".join([str(l) for l in lats])  # noqa: E741
    longs = track_segment_data[track_segment_data.moving].longitude.to_list()
    longs = ",".join([str(l) for l in longs])  # noqa: E741

    map_data = MapData(path=MapPathData(latitudes=lats, longitudes=longs))

    if segment_track.track.has_elevations():
        slope_colors = current_app.config.style.slope_colors
        plot2d = get_track_elevation_slope_plot(
            track=segment_track,
            color_neutral=slope_colors.neutral,
            color_min=slope_colors.min,
            color_max=slope_colors.max,
            intervals=20,
        )

        plot_elevation = json.dumps(plot2d, cls=PlotlyJSONEncoder)

    else:
        plot_elevation = None

    return render_template(
        "segments/show.html",
        active_page="segments",
        data=segment,
        map_data=map_data,
        plot_elevation=plot_elevation,
    )


@bp.route("/add", methods=("GET", "POST"))
def add_segment() -> str | Response:
    map_segment_form = AddMapSegmentForm()
    map_segment_form.segment_type.choices = [
        (s.id, s.text) for s in get_unique_model_objects_in_db(SegmentType)
    ]
    map_segment_form.segment_difficulty.choices = [
        (d.id, d.text) for d in get_unique_model_objects_in_db(Difficulty)
    ]

    if map_segment_form.validate_on_submit():
        points = [
            (float(lat), float(lng))
            for lat, lng in zip(
                map_segment_form.segment_latitudes.data.split(","),
                map_segment_form.segment_longitudes.data.split(","),
            )
        ]

        if (
            map_segment_form.segment_elevations.data is None
            or map_segment_form.segment_elevations.data == ""
        ):
            elevations = None
        else:
            elevations = [
                float(e) for e in map_segment_form.segment_elevations.data.split(",")
            ]

        track_for_segment = PyTrack(points=points, elevations=elevations, times=None)

        track_overview = track_for_segment.get_segment_overview()

        bounds = track_for_segment.track.get_bounds()
        if bounds is None:
            flash("Cound not determine bounds", "alert-danger")
        else:
            name = map_segment_form.segment_name.data
            description = None
            if (
                map_segment_form.segment_description.data != ""
                and map_segment_form.segment_description.data is not None
            ):
                description = map_segment_form.segment_description.data
            segment = DatabaseSegment(
                name=name,
                segment_type=orm_db.session.get(
                    SegmentType, int(map_segment_form.segment_type.data)
                ),
                difficulty=orm_db.session.get(
                    Difficulty, int(map_segment_form.segment_difficulty.data)
                ),
                description=description,
                distance=track_overview.total_distance,
                min_elevation=track_overview.min_elevation,
                max_elevation=track_overview.max_elevation,
                uphill_elevation=track_overview.uphill_elevation,
                downhill_elevation=track_overview.downhill_elevation,
                bounds_min_lat=bounds.min_latitude,
                bounds_max_lat=bounds.max_latitude,
                bounds_min_lng=bounds.min_longitude,
                bounds_max_lng=bounds.max_longitude,
                gpx=track_for_segment.get_xml().encode(),
            )

            orm_db.session.add(segment)
            try:
                orm_db.session.commit()
            except IntegrityError as e:
                flash("Error: %s" % e, "alert-danger")
            else:
                flash("Segment Added", "alert-success")
                return redirect("/segments")

    elif request.method == "POST":
        flash_form_error(map_segment_form)

    return render_template(
        "segments/add_from_map.html",
        active_page="add_segment",
        map_segment_form=map_segment_form,
    )


def get_router() -> Router:
    if "osm_router" not in g:
        logger.debug("Initializing router")
        g.osm_router = Router("cycle")
    return g.osm_router


@bp.route("/calc-route", methods=["POST"])
def calcualte_route() -> dict | tuple[dict, int]:
    config = current_app.config
    router = get_router()
    waypoints = request.json["waypoints"]  # type: ignore
    calc_route_for = [(waypoints[0], waypoints[1])]
    for waypoint in waypoints[2::]:
        i = len(calc_route_for) - 1
        calc_route_for.append((calc_route_for[i][1], waypoint))

    route_segments = []
    for i, ((start_lat, start_lng), (end_lat, end_lng)) in enumerate(calc_route_for):
        status, route = router.doRoute(
            router.findNode(start_lat, start_lng), router.findNode(end_lat, end_lng)
        )
        if status == "success":
            logger.debug("Found route for waypoints:")
            logger.debug("  Start: %s / %s", start_lat, start_lng)
            logger.debug("    End: %s / %s", end_lat, end_lng)
            route_lat_lons = list(map(router.nodeLatLon, route))
            route_segments.append(route_lat_lons)
        else:
            return {
                "error": (
                    f"Could not found route for waypoint set {i} : "
                    f"From {start_lat}, {start_lng} to {end_lat}, {end_lng}"
                )
            }, 400

    ret_route = merge_route_segments(route_segments)

    logger.warning(ret_route)
    if not ret_route:
        return {"error": "No waypoints found"}, 400

    track = PyTrack(ret_route, None, None)

    enhancer = None
    try:
        enhancer = get_enhancer(config.external.track_enhancer.name)(
            url=config.external.track_enhancer.url,
            **config.external.track_enhancer.kwargs.to_dict(),
        )
    except APIHealthCheckFailedError:
        logger.warning("Enhancer not available. Skipping elevation profile")

    generate_elevation_plot = False
    if enhancer is not None:
        try:
            enhancer.enhance_track(track.track, True)
        except APIResponseError:
            logger.error("Could not enhance track with elevation")
        else:
            generate_elevation_plot = True

    logger.debug("Interpolation track")
    track.interpolate_points_in_segment(25, 0)

    profile_plot_base64 = None
    if generate_elevation_plot:
        track_segment_data = track.get_segment_data(0)

        pois = []
        pois.append(
            (track_segment_data.iloc[0].latitude, track_segment_data.iloc[0].longitude)
        )

        for waypoint in waypoints[1:-1]:
            wp_lat, wp_lng = waypoint
            closest_idx = find_closest_elem_to_poi(
                track_segment_data.iloc[1:-1], wp_lat, wp_lng, True
            )
            pois.append(
                (
                    track_segment_data.iloc[closest_idx + 1].latitude,
                    track_segment_data.iloc[closest_idx + 1].longitude,
                )
            )

        pois.append(
            (
                track_segment_data.iloc[-1].latitude,
                track_segment_data.iloc[-1].longitude,
            )
        )

        colors = current_app.config.style.color_sequence
        profile_plot = get_track_elevation_plot(
            track,
            False,
            color_elevation=colors[0],
            pois=pois,
            color_poi=current_app.config.style.color_marker,
        )
        profile_plot_base64 = convert_fig_to_base64([profile_plot], 1400, 400)[0]

    route_coords, elevations, _ = track.get_point_data_in_segmnet(0)

    return {
        "route": route_coords,
        "elevations": elevations,
        "profile": profile_plot_base64,
    }


def merge_route_segments(
    segments: list[list[tuple[float, float]]]
) -> list[tuple[float, float]]:
    """
    Merge segements from multipel qaypoint poirs into a single segment. The goal
    is mostly to remove parts of the overall segment where a route from a waypoint
    to the next waypoints overlaps.

    Example:

    """
    merged_segments: list[tuple[float, float]] = []

    for segment in segments:
        if not merged_segments:
            merged_segments.extend(segment)
            continue
        for node0, node1 in zip(segment[:-1], segment[1:]):
            if merged_segments[-1] == node0 and merged_segments[-2] == node1:
                merged_segments.pop()
            elif merged_segments[-1] == node0 and merged_segments[-2] != node1:
                merged_segments.append(node1)
            else:
                merged_segments.append(node0)
    return merged_segments


@bp.route("/segments-in-bounds", methods=["POST"])
def get_segments_in_bounds() -> tuple[dict, int] | str:
    try:
        received_request = SegmentsInBoundsRequest(**request.json)
    except ValidationError:
        return {
            "error": "Pass ne_latitude, ne_longitude, sw_latitude, and sw_longitude"
        }, 400

    config = current_app.config

    color_mapping_ = config.mappings.segment_types

    color_mapping = defaultdict(
        lambda: color_mapping_["default"],
        {k: v for k, v in color_mapping_.items() if k != "default"},
    )
    url_base = url_for("segments.show_segment", id_segment=0).replace("0", "")

    segments = get_segments_for_map_in_bounds(
        received_request.ids_on_map,
        received_request.ne_latitude,
        received_request.ne_longitude,
        received_request.sw_latitude,
        received_request.sw_longitude,
        color_mapping,
        url_base,
    )

    return SegmentsInBoundsResponse(segments=segments).json()
