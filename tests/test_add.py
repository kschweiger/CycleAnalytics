import uuid

from flask import Flask
from flask.testing import FlaskClient

from cycle_analytics.database.model import Ride
from cycle_analytics.database.model import db as orm_db


def test_add_note_ride_has_note(app: Flask, client: FlaskClient) -> None:
    test_ride: Ride = None
    with app.app_context():
        for ride in Ride.query.all():
            if ride.notes:
                test_ride = ride
                break

        assert test_ride is not None

        ride_id = test_ride.id
        prev_note_id = test_ride.notes[0].id

    new_text = str(uuid.uuid4())

    response = client.post(
        f"ride/add_note/{test_ride.id}",
        data={"note": new_text},
    )
    assert response.status_code == 302

    with app.app_context():
        ride = orm_db.get_or_404(Ride, ride_id)
        assert ride.notes[0].text == new_text
        # Test if the note has been modified and not recreated
        assert ride.notes[0].id == prev_note_id


def test_add_note_ride_no_note(app: Flask, client: FlaskClient) -> None:
    test_ride: Ride = None
    with app.app_context():
        for ride in Ride.query.all():
            if not ride.notes:
                test_ride = ride
                break

        assert test_ride is not None

        ride_id = test_ride.id

    new_text = str(uuid.uuid4())

    response = client.post(
        f"ride/add_note/{test_ride.id}",
        data={"note": new_text},
    )
    assert response.status_code == 302

    with app.app_context():
        ride = orm_db.get_or_404(Ride, ride_id)
        assert ride.notes[0].text == new_text
