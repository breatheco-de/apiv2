#!/bin/env bash

CELERY_MIN_WORKERS=${CELERY_MIN_WORKERS:-2}
CELERY_MAX_WORKERS=${CELERY_MAX_WORKERS:-2}
CELERY_PREFETCH_MULTIPLIER=${CELERY_PREFETCH_MULTIPLIER:-1}

CELERY_POOL=${CELERY_POOL:-prefork}
LOG_LEVEL=${LOG_LEVEL:-INFO}

export NEW_RELIC_METADATA_COMMIT=$HEROKU_SLUG_COMMIT;
export CORALOGIX_SUBSYSTEM=celeryworker;
export CELERY_WORKER_RUNNING=True;
export REMAP_SIGTERM=SIGQUIT;
export CELERY_POOL=$CELERY_POOL;

# it will be used by upload_activities
export CELERY_MAX_WORKERS=$CELERY_MAX_WORKERS;

if [ "$CELERY_POOL" == "gevent" ] || [ "$CELERY_POOL" == "prefork" ]; then
    SCALING="--autoscale=$CELERY_MIN_WORKERS,$CELERY_MAX_WORKERS"
else
    SCALING="--concurrency=$CELERY_MAX_WORKERS"
fi


current_timestamp=$(date +%s)
num_processes=$(((current_timestamp + $RANDOM) % 100))

# generate a random pid
for ((i=1; i<=$num_processes; i++)); do
    true &
done

wait

newrelic-admin run-program bin/start-pgbouncer \
    python -m celery -A breathecode.celery worker --loglevel=$LOG_LEVEL \
        --prefetch-multiplier=$CELERY_PREFETCH_MULTIPLIER --pool=$CELERY_POOL \
        $SCALING --without-gossip --without-mingle
