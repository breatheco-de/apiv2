# Environment variables

This article only includes the environment variables related to the infrastructure.

## WEB_WORKER_CONNECTION

The maximum number of simultaneous clients.

### Default

200

### References

- [Gunicorn documentation](https://docs.gunicorn.org/en/stable/settings.html#worker-connections).

### Where it is used

- `scripts/dyno/web.sh`

### Note

- Maybe this variable should be called `WEB_WORKER_CONNECTIONS` instead

## WEB_TIMEOUT

- Time to wait to send the web request, worker that exceeds that time will be killed and restarted.

### Default

29

### References

- [Gunicorn documentation](https://docs.gunicorn.org/en/stable/settings.html#timeout).

### Where it is used

- `scripts/dyno/web.sh`

## WEB_WORKERS

Number of workers that respond to web requests.

### Default

2

### References

- [Gunicorn documentation](https://docs.gunicorn.org/en/stable/settings.html#workers).

### Where it is used

- `scripts/dyno/web.sh`

## WEB_WORKER_CLASS

Worker to be used within `Gunicorn`.

### Default

gevent

### References

- [Gunicorn documentation](https://docs.gunicorn.org/en/stable/settings.html#worker-class).

## LOG_LEVEL

Define the minimum log level to show.

### Default

INFO

### Where it is used

- `scripts/dyno/celeryworker.sh`
- `breathecode/settings.py`

## CELERY_MIN_WORKERS

Minimum workers to be up.

### Default

2

### References

- [Celery documentation](https://docs.celeryq.dev/en/main/internals/reference/celery.worker.autoscale.html#celery-worker-autoscale).

### Where it is used

- `scripts/dyno/celeryworker.sh`

## CELERY_MAX_WORKERS

Maximum workers to be up.

### Default

2

### References

- [Celery documentation](https://docs.celeryq.dev/en/main/internals/reference/celery.worker.autoscale.html#celery-worker-autoscale).

### Where it is used

- `scripts/dyno/celeryworker.sh`

## CELERY_PREFETCH_MULTIPLIER

Number of messages that will be accepted by each worker.

### Default

4

### References

- [Celery documentation](https://docs.celeryq.dev/en/stable/userguide/configuration.html#worker-prefetch-multiplier).

### Where it is used

- `scripts/dyno/celeryworker.sh`

## CELERY_POOL

Worker class that will manage the concurrency.

### Default

prefork

### References

- [Celery documentation](https://docs.celeryq.dev/en/stable/userguide/configuration.html#worker-prefetch-multiplier).

### Where it is used

- `scripts/dyno/celeryworker.sh`
