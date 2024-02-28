from typing import Generator

import pytest
from flask import Flask
from flask.testing import FlaskClient
from pytest_mock import MockerFixture
from werkzeug.datastructures import MultiDict

from cycle_analytics import ride
from cycle_analytics.database.model import Ride, TrackOverview, ride_track
from cycle_analytics.database.model import db as orm_db
from cycle_analytics.utils.base import unwrap


@pytest.fixture()
def ride_id_and_overview_ids(
    app: Flask,
) -> Generator[tuple[int, list[int]], None, None]:
    with app.app_context():
        overview_id_track = list(  # noqa: RUF015
            unwrap(
                orm_db.session.query(TrackOverview.id_track)
                .filter(TrackOverview.id_segment.isnot(None))
                .distinct()
                .first()
            )
        )[0]
        ride_id, _ = unwrap(
            orm_db.session.query(ride_track)
            .filter_by(track_id=overview_id_track)
            .first()
        )
        ride = unwrap(orm_db.session.query(Ride).filter(Ride.id == ride_id).first())
        track = next(iter([t for t in ride.tracks if t.id == overview_id_track]))
        segment_overview_ids = [
            o.id for o in track.overviews if o.id_segment is not None
        ]

    yield ride_id, segment_overview_ids

    with app.app_context():
        segment_overviews = unwrap(
            orm_db.session.query(TrackOverview)
            .filter(TrackOverview.id.in_(segment_overview_ids))
            .all()
        )
        print(segment_overviews)
        for overview in segment_overviews:
            overview.of_interest = True
        orm_db.session.add_all(segment_overviews)
        orm_db.session.commit()


@pytest.mark.parametrize(
    ("initial_interest_values", "toggled", "expected", "mod_func_call_count"),
    [
        ([True, True], [True, True], [True, True], 0),
        ([True, True], [True, False], [True, False], 1),
        ([True, False], [True, True], [True, True], 1),
        ([False, False], [False, True], [False, True], 1),
    ],
)
def test_laps_modification(
    mocker: MockerFixture,
    app: Flask,
    client: FlaskClient,
    ride_id_and_overview_ids: tuple[int, list[int]],
    initial_interest_values: list[bool],
    toggled: list[bool],
    expected: list[bool],
    mod_func_call_count: int,
) -> None:
    spy_modifier = mocker.spy(ride, "switch_overview_of_interest_flag")
    print(ride_id_and_overview_ids)
    id_ride, id_overviews = ride_id_and_overview_ids
    assert len(id_overviews) == len(initial_interest_values)
    assert len(id_overviews) == len(toggled)

    with app.app_context():
        overviews = unwrap(
            orm_db.session.query(TrackOverview)
            .filter(TrackOverview.id.in_(id_overviews))
            .all()
        )
        for o, f in zip(overviews, initial_interest_values):
            o.of_interest = f
        orm_db.session.add_all(overviews)
        orm_db.session.commit()

    _post_data: list[tuple[str, str]] = [("updated_hidden_state", "1")]
    for io, inital, is_toggled in zip(id_overviews, initial_interest_values, toggled):
        _post_data.append(
            (f"current_value_segment_hide_{io}", str(int(inital))),
        )
        if is_toggled:
            _post_data.append(
                (f"segment_hide_checkbox_{io}", "on"),
            )

    post_data = MultiDict(_post_data)

    response = client.post(
        f"/ride/{id_ride}",
        data=post_data,
        follow_redirects=True,
    )

    assert response.status_code == 200

    assert spy_modifier.call_count == mod_func_call_count

    with app.app_context():
        overviews = unwrap(
            orm_db.session.query(TrackOverview)
            .filter(TrackOverview.id.in_(id_overviews))
            .all()
        )
        for o, e in zip(overviews, expected):
            assert o.of_interest == e
