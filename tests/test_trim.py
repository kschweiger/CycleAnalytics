from flask import Flask
from flask.testing import FlaskClient


def test_trim_upload_state(app: Flask, client: FlaskClient) -> None:
    response = client.get("/track/trim/")
    assert response.status_code == 200

    exp_form_input = '<input accept=".gpx,.fit" class="form-control" id="track" name="track" required type="file">'
    assert exp_form_input in response.text


def test_trim_track_initial_state(app: Flask, client: FlaskClient) -> None:
    response = client.get("/track/trim/?track_id=2")
    assert response.status_code == 200

    assert 'div id="map"' in response.text
