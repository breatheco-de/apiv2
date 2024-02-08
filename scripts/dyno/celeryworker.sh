#!/bin/env bash

CELERY_MIN_WORKERS=${CELERY_MIN_WORKERS:-2}
CELERY_MAX_WORKERS=${CELERY_MAX_WORKERS:-2}
CELERY_PREFETCH_MULTIPLIER=${CELERY_PREFETCH_MULTIPLIER:-4}
CELERY_POOL=${CELERY_POOL:-prefork}
CELERY_CONCURRENCY=${CELERY_CONCURRENCY:-4}
LOG_LEVEL=${LOG_LEVEL:-INFO}

export NEW_RELIC_METADATA_COMMIT=$HEROKU_SLUG_COMMIT;
export CORALOGIX_SUBSYSTEM=celeryworker;
export CELERY_WORKER_RUNNING=True;
export REMAP_SIGTERM=SIGQUIT;

# it will be used by upload_activities
export CELERY_MAX_WORKERS=$CELERY_MAX_WORKERS;

newrelic-admin run-program bin/start-pgbouncer-stunnel \
    celery -A breathecode.celery worker --loglevel=$LOG_LEVEL \
        --prefetch-multiplier=$CELERY_PREFETCH_MULTIPLIER --pool=$CELERY_POOL \
        --autoscale=$CELERY_MIN_WORKERS,$CELERY_MAX_WORKERS --concurrency=$CELERY_CONCURRENCY
