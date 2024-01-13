# Web

## Studies

- [Django workers](./studies/django-workers.md)
- [HTTP client](./studies/http-clients.md)

## Setup

### Worker

Gunicorn + Uvicorn.

### HTTP client

#### Sync

Requests.

#### Async

AIOHTTP.

## Next step

### Strategy about blocking code

1. All blocking code will be split in db and others.
2. Make a `v2` to all endpoints with blocking code from the category others.
3. All new endpoints that use blocking code must use async functions.
4. All blocking code from the category db is sync, I think that forcing a massive migration should be a bit useless, django just wrote a wrapper.

### Study async replacements to the actual libs

Sometimes the async libs work significantly faster than sync libraries, it is necessary to collect those cases and use those libs, you must take into consideration that some codes are faster using sync code.

### See how progress Uvicorn

Uvicorn is the most stable worker, if it fails we must study how do works Hypercorn with Evloop.
