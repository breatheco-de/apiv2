# fttests — Functional smoke tests

CLI to run functional tests against deployed environments (e.g., dev/prod) from the terminal. It uses only the Python standard library — no extra dependencies.

## Usage

```
python -m scripts.fttests list
python -m scripts.fttests <feature>
```

Exit codes:

- `0`: success
- `1`: failure (assertion error, missing dependencies, or unexpected error)

## Writing tests (auto-discovery)

Features are subpackages under `scripts/fttests/`. Any function named `test_*` inside the feature package (its `__init__.py` and direct submodules) is auto-discovered and executed.

Conventions:

- Test functions are named `test_*`.
- Raise `AssertionError` on failure; return `None` on success.
- Use helpers from `scripts/fttests/utils.py` for HTTP calls and output.

Minimal example (`scripts/fttests/subscription_seats/list.py`):

```python
from __future__ import annotations
import os
from ..utils import http_request, print_section

def test_list_seats():
    print_section("subscription_seats: list seats (example)")
    base = os.environ["FTT_BASE_URL"].rstrip("/")
    path = os.getenv("FTT_SEATS_LIST_PATH", "/v1/subscriptions/seats")
    url = f"{base}{path if path.startswith('/') else '/' + path}"
    status, headers, body = http_request("GET", url)
    assert 200 <= status < 400, f"list seats failed with status {status}"
```

Note: The package `__init__.py` can be empty. You can keep all tests in submodules.

## New: sequential execution with shared context

The runner now supports sequential, stateful execution:

- Tests are grouped by module. Inside each module, tests run in definition order.
- Optional `setup()` runs before the module’s tests; optional `teardown()` runs after.
- `setup()`, each `test_*`, and `teardown()` can receive a shared context as named parameters.
- If a function returns a `dict`, it is merged into the context for subsequent steps.
- If `setup()` fails, that module’s tests and `teardown()` are skipped; other modules still run.
- Failures do not abort the whole feature; a summary is printed at the end.

Example (`scripts/fttests/my_feature/__init__.py`):

```python
from __future__ import annotations
import os
from ..utils import assert_env_vars, http_request, print_section

def check_dependencies() -> None:
    assert_env_vars(["FTT_BASE_URL"])  # add more as needed

def setup():
    base = os.environ["FTT_BASE_URL"].rstrip("/")
    token = os.getenv("FTT_API_TOKEN")
    auth_headers = {"Authorization": f"Bearer {token}"} if token else {}
    return {"base_url": base, "auth_headers": auth_headers}

def test_health(base_url: str):
    print_section("health")
    status, _, _ = http_request("GET", f"{base_url}/")
    assert 200 <= status < 400

def test_list(base_url: str, auth_headers: dict):
    status, _, body = http_request("GET", f"{base_url}/v1/items", headers=auth_headers)
    assert status == 200
    return {"items_body": body}

def teardown(**_):
    # Optionally clean up using values from the context
    pass
```

Tip: functions can declare only the context keys they need (e.g., `base_url`). If a function accepts `**kwargs`, it will receive the entire context.

## Add a new feature

1. Create a new directory: `scripts/fttests/<feature_name>/__init__.py`
2. Optionally implement `check_dependencies()`; add one or more modules with `test_*` functions.
3. Use helpers from `scripts/fttests/utils.py`:
   - `assert_env_vars([...])`
   - `http_request(method, url, headers=..., data=...)`
   - `print_section(title)`

## CI notes

- This runner is intended to replace manual Postman checks.
- Keep tests idempotent and safe to run repeatedly against dev environments.
- Prefer read-only or dedicated test endpoints. If you must create resources, clean up.

## Example: subscription_seats

Environment variables:

- `FTT_BASE_URL` (required)
- `FTT_API_TOKEN` (optional)
- `FTT_HEALTH_PATH` (optional, default `/`)
- `FTT_SEATS_LIST_PATH` (optional, e.g. `/v1/subscriptions/seats`)

Run:

```
FTT_BASE_URL=https://<your-app>.herokuapp.com \
FTT_SEATS_LIST_PATH=/v1/subscriptions/seats \
FTT_API_TOKEN=<token-if-needed> \
python -m scripts.fttests subscription_seats
```

This will:

- Run `check_dependencies()` if present.
- Auto-discover and run `test_*` in `scripts/fttests/subscription_seats/` sequentially per module.
- Continue after failures and summarize results at the end.
