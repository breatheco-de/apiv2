.PHONY: test

# project ID
PROJECT_ID := test

# docker image for BigQuery emulator
BQ_EMULATOR_IMAGE := ghcr.io/goccy/bigquery-emulator:latest

# target to run the test, it does not work yet, maybe it must be removed
test:
	docker pull $(BQ_EMULATOR_IMAGE)
	# docker pull $(BQ_EMULATOR_IMAGE) --project=$(PROJECT_ID)
	docker run -d -p 8086:8086 --name bigquery-emulator $(BQ_EMULATOR_IMAGE)

	pipenv run test breathecode/activity/tests/urls/v2/tests_me_activity.py

	docker ps
	# insert your test command here
	docker stop bigquery-emulator
	docker rm bigquery-emulator

bigquery-emulator:
	docker pull $(BQ_EMULATOR_IMAGE)
	docker run -d -p 8086:8086 --name bigquery-emulator $(BQ_EMULATOR_IMAGE)
