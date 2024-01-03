test-cov:
	pytest  --cov=cycle_analytics tests --cov-report xml:cov.xml --cov-report term --disable-warnings