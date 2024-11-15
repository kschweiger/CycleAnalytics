from flask.testing import FlaskClient


def test_initial_state(client: FlaskClient) -> None:
    response = client.get("/track/add_segments/2")
    assert response.status_code == 200


def test_redirect_track_w_segment(client: FlaskClient) -> None:
    response = client.get("/track/add_segments/4", follow_redirects=False)
    assert response.status_code == 302


def test_no_redirect_track_w_segment(client: FlaskClient) -> None:
    response = client.get("/track/add_segments/4?force=1", follow_redirects=False)
    assert response.status_code == 200


def test_preview_state(client: FlaskClient) -> None:
    response = client.post(
        "/track/add_segments/2",
        data={"submit_type": "preview", "submit_indices": "100"},
    )
    assert response.status_code == 200

    assert '<h5 class="text-info">Preview</h5>' in response.text
