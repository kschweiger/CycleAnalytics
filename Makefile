test-cov:
	pytest  --cov=cycle_analytics tests --cov-report xml:cov.xml --cov-report term --disable-warnings

build:
	docker compose --file docker/docker-compose.yml  build

run-prod:
	docker compose -f docker/docker-compose.yml  up

run-dev:
	docker compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml  up

run-debug:
	docker compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml -f docker/docker-compose.debug.yml up

uv-compile:
	uv pip compile pyproject.toml -o requirements/prod.txt --all-extras --no-header
	uv pip compile requirements/dev.in -o requirements/dev.txt --no-header -U
	uv pip compile requirements/test.in -o requirements/test.txt --no-header -U

uv-compile-update:
	uv pip compile pyproject.toml -o requirements/prod.txt --all-extras --no-header -U
	uv pip compile requirements/dev.in -o requirements/dev.txt --no-header -U
	uv pip compile requirements/test.in -o requirements/test.txt --no-header -U

uv-sync:
	uv pip sync requirements/prod.txt requirements/dev.txt requirements/test.txt
	uv pip install -e . --no-deps
