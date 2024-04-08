import importlib.resources

from flask import Flask
from flask.testing import FlaskClient
from werkzeug.datastructures import MultiDict

from cycle_analytics.database.retriever import (
    get_rides_with_tracks,
)
from tests import resources


def test_view_compare_tracks_post_tracks(app: Flask, client: FlaskClient) -> None:
    response = client.get("/track/compare/")
    assert response.status_code == 200
    assert '<div id="map_plot"' not in response.text

    with app.app_context():
        ride_data = get_rides_with_tracks()
    assert len(ride_data) >= 2

    post_data = MultiDict(
        [
            ("track_choice", f"{ride_data[0][1].isoformat()} - ID: {ride_data[0][0]}"),
            ("track_choice", f"{ride_data[1][1].isoformat()} - ID: {ride_data[1][0]}"),
        ]
    )

    response = client.post("/track/compare/", data=MultiDict(post_data))
    assert response.status_code == 200

    assert '<div id="map_plot"' in response.text


def test_view_compare_tracks_post_tracks_same_track_twice(
    app: Flask, client: FlaskClient
) -> None:
    response = client.get("/track/compare/")
    assert response.status_code == 200
    assert '<div id="map_plot"' not in response.text

    with app.app_context():
        ride_data = get_rides_with_tracks()
    assert len(ride_data) >= 2

    post_data = MultiDict(
        [
            ("track_choice", f"{ride_data[0][1].isoformat()} - ID: {ride_data[0][0]}"),
            ("track_choice", f"{ride_data[0][1].isoformat()} - ID: {ride_data[0][0]}"),
        ]
    )

    response = client.post("/track/compare/", data=MultiDict(post_data))
    assert response.status_code == 200

    assert '<div id="map_plot"' not in response.text
    assert (
        '<div class="alert alert-danger">Same ride passed mutliple times</div>'
        in response.text
    )


def test_view_compare_tracks_post_tracks_invalid_choice(client: FlaskClient) -> None:
    post_data = MultiDict([("track_choice", "foo bar baz")])

    response = client.post("/track/compare/", data=MultiDict(post_data))
    assert response.status_code == 200

    assert '<div id="map_plot"' not in response.text
    assert '<div class="alert alert-danger">Invalid ride choice' in response.text


def test_view_compare_tracks_post_files(app: Flask, client: FlaskClient) -> None:
    resource_files = importlib.resources.files(resources)

    response = client.get("/track/compare/")
    assert response.status_code == 200
    assert '<div id="map_plot"' not in response.text

    post_data = MultiDict(
        [
            (
                "compare_file",
                (resource_files / "Freiburger_Münster_nach_Schau_Ins_Land.gpx").open(
                    "rb"
                ),
            ),
            (
                "compare_file",
                (resource_files / "Teilstueck_Schau_ins_land.gpx").open("rb"),
            ),
        ]
    )

    response = client.post("/track/compare/", data=MultiDict(post_data))
    assert response.status_code == 200

    assert '<div id="map_plot"' in response.text


def test_view_compare_tracks_post_files_same_file_twice(
    app: Flask, client: FlaskClient
) -> None:
    resource_files = importlib.resources.files(resources)

    response = client.get("/track/compare/")
    assert response.status_code == 200
    assert '<div id="map_plot"' not in response.text

    post_data = MultiDict(
        [
            (
                "compare_file",
                (resource_files / "Freiburger_Münster_nach_Schau_Ins_Land.gpx").open(
                    "rb"
                ),
            ),
            (
                "compare_file",
                (resource_files / "Freiburger_Münster_nach_Schau_Ins_Land.gpx").open(
                    "rb"
                ),
            ),
        ]
    )

    response = client.post("/track/compare/", data=MultiDict(post_data))
    assert response.status_code == 200

    assert '<div id="map_plot"' not in response.text
    assert (
        '<div class="alert alert-danger">Same file passed mutliple times'
        in response.text
    )


def test_view_compare_tracks_post_tracks_and_files(
    app: Flask, client: FlaskClient
) -> None:
    resource_files = importlib.resources.files(resources)

    response = client.get("/track/compare/")
    assert response.status_code == 200
    assert '<div id="map_plot"' not in response.text

    with app.app_context():
        ride_data = get_rides_with_tracks()
    assert len(ride_data) >= 2

    post_data = MultiDict(
        [
            (
                "compare_file",
                (resource_files / "Freiburger_Münster_nach_Schau_Ins_Land.gpx").open(
                    "rb"
                ),
            ),
            (
                "compare_file",
                (resource_files / "Teilstueck_Schau_ins_land.gpx").open("rb"),
            ),
            ("track_choice", f"{ride_data[0][1].isoformat()} - ID: {ride_data[0][0]}"),
            ("track_choice", f"{ride_data[1][1].isoformat()} - ID: {ride_data[1][0]}"),
        ]
    )

    response = client.post("/track/compare/", data=MultiDict(post_data))
    assert response.status_code == 200

    assert '<div id="map_plot"' in response.text
