# Functional smoke tests runner (fttests)

CLI to run functional tests against deployed environments (e.g., Heroku dev/prod)
without Postman or a UI. Uses only the Python standard library — no extra deps.

## Usage

```
python -m scripts.fttests list
python -m scripts.fttests <feature>
```

Exit codes:

- `0`: success
- `1`: failure (assertion error, missing dependencies, or unexpected error)

## Environment variables

Common variables consumed by features via `scripts/fttests/utils.py`:

- `FTT_BASE_URL` (required): Base URL of the API, e.g. `https://apiv2-dev.herokuapp.com`
- `FTT_API_TOKEN` (optional): Bearer token for protected endpoints
- `FTT_HEALTH_PATH` (optional): Path for a simple reachability check, default `/`

Features may define additional required variables; check each feature's docs.

## Features

Features are subpackages under `scripts/fttests/` with this contract:

- `check_dependencies() -> None`: Validate required env vars or preconditions. Must raise `AssertionError` (or call `sys.exit(1)`) on failure.
- `run() -> None`: Execute the functional test flow. Must raise `AssertionError` (or call `sys.exit(1)`) on failure.

Example skeleton: see `scripts/fttests/subscription_seats/`.

## Add a new feature

1. Create a new directory: `scripts/fttests/<feature_name>/__init__.py`
2. Implement `check_dependencies()` and `run()`.
3. Use helpers from `scripts/fttests/utils.py`:
   - `assert_env_vars([...])`
   - `build_headers(token_env="FTT_API_TOKEN")`
   - `http_request(method, url, headers=..., data=...)`
   - `print_section(title)`

Minimal example:

```python
from __future__ import annotations
import os
from ..utils import assert_env_vars, build_headers, http_request, print_section

def check_dependencies() -> None:
    assert_env_vars(["FTT_BASE_URL"])  # add more as needed

def run() -> None:
    print_section("my_feature: smoke test")
    base = os.environ["FTT_BASE_URL"].rstrip("/")
    status, _, _ = http_request("GET", f"{base}/health")
    assert 200 <= status < 400
```

## CI notes

- This runner is intended to replace manual Postman checks.
- Keep tests idempotent and safe to run repeatedly against dev environments.
- Prefer read-only or dedicated test endpoints. If you must create resources, clean up.


## Feature: subscription_seats

Environment variables:

- `FTT_BASE_URL` (required)
- `FTT_API_TOKEN` (optional)
- `FTT_HEALTH_PATH` (optional, default `/`)
- `FTT_SEATS_LIST_PATH` (optional, e.g. `/v1/subscriptions/seats` to enable the list test)

Run example:

```
FTT_BASE_URL=https://<your-heroku-app>.herokuapp.com \
FTT_SEATS_LIST_PATH=/v1/subscriptions/seats \
FTT_API_TOKEN=<token-if-needed> \
python3 -m scripts.fttests subscription_seats
```
