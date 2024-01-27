# Journal

## Notes

- RPM: request per minute.
- `/v1/admissions/cohort/all`: a light endpoint cached.
- `/v1/admissions/syllabus/version`: a heavy endpoint cached.

## 01/12/2024

- `[dev]` switch `WEB_WORKER_CLASS` from `gevent` to `uvicorn.workers.UvicornWorker`.
- `[dev]` switch `WEB_WORKERS` from `1` to `2`.
- `[dev]` switch `WEB_WORKER_CONNECTION` from `120` to `160`.

Side effects:

- Support to async in Django.
- Memory up from 265MB to 437MB.
- `/v1/admissions/cohort/all` and `/v1/admissions/syllabus/version` changed from 35 RPM both to 133 RPM #1 and 31 RPM #2, this should change with each attempt.

## 01/15/2024

- `[all]` `django_minify_html` was added to the middlewares.
- `[prod]` `make_charges` frequency changed from `every 10 minutes` to `Daily at 12:00 AM UTC`.

## 01/16/2024

- `[prod]` set `CELERY_DYNOS` to `2`.
- `[prod]` set `CELERY_MAX_WORKERS` to `3`.
- `[dev]` switch `CELERY_MAX_WORKERS` from `1` to `2`.

## 01/17/2024

- `[all]` `STATIC_BUCKET` setted.

Side effects:

- `/v1/admissions/cohort/all` changed from 133 RPM both to 145 - 170 (one time) RPM, this should change with each attempt.

## 01/24/2024

- `[prod]` preboot was enabled.
- `[prod]` switch `WEB_WORKER_CLASS` from `gevent` to `uvicorn.workers.UvicornWorker`.
- `[prod]` switch `LOG_LEVEL` from `DEBUG` to `WARNING`.
- `[prod]` set `WEB_MAX_REQUESTS` to `6000`.
- `[prod]` set `WEB_MAX_REQUESTS_JITTER` to `3000`.
- `[dev]` set `WEB_MAX_REQUESTS` to `100`.
- `[dev]` set `WEB_MAX_REQUESTS_JITTER` to `50`.

Side effects:

- In dev, this prevents the server could getting out of memory.
- In prod, this helps to have sufficient memory to add a third worker.
- If the server would have 1000 requests each 10 minutes, this would restart the worker each 60-90 minutes.

## 01/25/2024

- `[prod]` switch `WEB_MAX_REQUESTS` from `6000` to `3000`.
- `[prod]` switch `WEB_MAX_REQUESTS_JITTER` from `3000` to `1500`.

Reasons for the change:

- Web worker was reaching 841 MB ram.
