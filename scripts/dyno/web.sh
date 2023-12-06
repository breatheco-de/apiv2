#!/bin/env bash

WEB_WORKER_CONNECTION=${WEB_WORKER_CONNECTION:-200}
WEB_WORKER_CLASS=${WEB_WORKER_CLASS:-gevent}
WEB_WORKERS=${WEB_WORKERS:-2}
WEB_TIMEOUT=${WEB_TIMEOUT:-29}

export NEW_RELIC_METADATA_COMMIT=$HEROKU_SLUG_COMMIT;
export CORALOGIX_SUBSYSTEM=web;
newrelic-admin run-program bin/start-pgbouncer-stunnel \
    gunicorn breathecode.wsgi --timeout $WEB_TIMEOUT --workers $WEB_WORKERS \
        --worker-connections $WEB_WORKER_CONNECTION --worker-class $WEB_WORKER_CLASS
