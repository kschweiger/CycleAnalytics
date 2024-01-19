test-cov:
	pytest  --cov=cycle_analytics tests --cov-report xml:cov.xml --cov-report term --disable-warnings

compose-build:
	docker compose  build

run-prod:
	docker-compose up

run-dev:
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml  up

run-debug:
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml -f docker-compose.debug.yml up