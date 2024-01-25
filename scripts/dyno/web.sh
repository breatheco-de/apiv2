#!/bin/env bash

WEB_WORKER_CONNECTION=${WEB_WORKER_CONNECTION:-200}
WEB_WORKER_CLASS=${WEB_WORKER_CLASS:-gevent}
WEB_WORKERS=${WEB_WORKERS:-2}
WEB_TIMEOUT=${WEB_TIMEOUT:-29}
WEB_MAX_REQUESTS=${WEB_MAX_REQUESTS:-6000}
WEB_MAX_REQUESTS_JITTER=${WEB_MAX_REQUESTS_JITTER:-3000}
WEB_PRELOAD=${WEB_PRELOAD:-0}

export NEW_RELIC_METADATA_COMMIT=$HEROKU_SLUG_COMMIT;
export CORALOGIX_SUBSYSTEM=web;

if [ "$WEB_PRELOAD" = "1" ]; then
    EXTRA="--preload"
else
    EXTRA=""
fi

if [ "$WEB_WORKER_CLASS" = "uvicorn.workers.UvicornWorker" ]; then
    export SERVER_TYPE=asgi;
else
    export SERVER_TYPE=wsgi;
fi

newrelic-admin run-program bin/start-pgbouncer-stunnel \
    gunicorn breathecode.$SERVER_TYPE --timeout $WEB_TIMEOUT --workers $WEB_WORKERS \
        --worker-connections $WEB_WORKER_CONNECTION --worker-class $WEB_WORKER_CLASS \
        --max-requests $WEB_MAX_REQUESTS --max-requests-jitter $WEB_MAX_REQUESTS_JITTER \
        $EXTRA
