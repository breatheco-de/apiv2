.PHONY: test

# project ID
PROJECT_ID := test

# docker image for BigQuery emulator
BQ_EMULATOR_IMAGE := ghcr.io/goccy/bigquery-emulator:latest
HEROKU_SLUG_COMMIT := $(shell git rev-parse HEAD)

new-relic:
	@echo ${NEW_RELIC_LICENSE_KEY}
	@echo "license_key: ${NEW_RELIC_LICENSE_KEY}" | tee -a /etc/newrelic-infra.yml
	newrelic-infra

release:
	@export CORALOGIX_SUBSYSTEM=web; \
		export NEW_RELIC_METADATA_COMMIT=${HEROKU_SLUG_COMMIT}; \
		# newrelic-admin run-program bin/start-pgbouncer \
		gunicorn breathecode.wsgi --timeout 29 --workers ${WEB_WORKERS} \
		--worker-connections ${WEB_WORKER_CONNECTION} --worker-class ${WEB_WORKER_CLASS}

web:
	@export CORALOGIX_SUBSYSTEM=web; \
		export NEW_RELIC_METADATA_COMMIT=${HEROKU_SLUG_COMMIT}; \
		# newrelic-admin run-program bin/start-pgbouncer \
		gunicorn breathecode.wsgi --timeout 29 --workers ${WEB_WORKERS} \
		--worker-connections ${WEB_WORKER_CONNECTION} --worker-class ${WEB_WORKER_CLASS}

# target to run the test, it does not work yet, maybe it must be removed
test:
	# docker pull $(BQ_EMULATOR_IMAGE)
	# # docker pull $(BQ_EMULATOR_IMAGE) --project=$(PROJECT_ID)
	# docker run -d -p 8086:8086 --name bigquery-emulator $(BQ_EMULATOR_IMAGE)

	poetry run pytest

	docker ps
	# insert your test command here
	docker stop bigquery-emulator
	docker rm bigquery-emulator

bigquery-emulator:
	docker pull $(BQ_EMULATOR_IMAGE)
	docker run -d -p 8086:8086 --name bigquery-emulator $(BQ_EMULATOR_IMAGE)


start:
	python manage.py runserver 0.0.0.0:8000
