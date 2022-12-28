import pytest

from cycle_analytics import create_app


@pytest.fixture
def app():
    app = create_app(
        {
            "TESTING": True,
        }
    )

    app.config["SERVER_NAME"] = "localhost"

    return app


@pytest.fixture
def client(app):
    return app.test_client()
