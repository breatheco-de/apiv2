"""
Shared helpers for functional tests executed via `python -m scripts.fttests <feature>`.
Only standard library modules are used to avoid new dependencies.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from typing import Dict, Iterable, Optional, Tuple

# ANSI colors (basic) for visibility in CI/terminal
RED = "\033[31m"
RESET = "\033[0m"


def assert_env_vars(names: Iterable[str]) -> None:
    """Assert that all environment variables in `names` are set and non-empty.

    Raises AssertionError with a helpful message if any are missing.
    """
    missing = [name for name in names if not os.getenv(name)]
    if missing:
        raise AssertionError("Missing required environment variables: " + ", ".join(missing))


def build_headers(token_env: str | None = None, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    headers: Dict[str, str] = {"User-Agent": "fttests/1.0 (+https://4geeks.com)"}
    if token_env:
        token = os.getenv(token_env)
        if token:
            headers["Authorization"] = f"Bearer {token}"
    if extra:
        headers.update(extra)
    return headers


def http_request(
    method: str,
    url: str,
    headers: Optional[Dict[str, str]] = None,
    data: Optional[Dict[str, object] | bytes] = None,
    timeout: int = 20,
) -> Tuple[int, Dict[str, str], bytes]:
    """Make an HTTP request using the stdlib.

    - method: HTTP method (GET, POST, etc.)
    - url: full URL
    - headers: request headers
    - data: dict (will be JSON-encoded) or raw bytes
    - timeout: seconds

    Returns (status_code, response_headers, body_bytes)
    Raises urllib.error.URLError on network issues.
    """
    body: Optional[bytes]
    if isinstance(data, bytes) or data is None:
        body = data
    else:
        body = json.dumps(data).encode("utf-8")
        headers = {**(headers or {}), "Content-Type": "application/json"}

    req = urllib.request.Request(url=url, method=method.upper(), headers=headers or {}, data=body)
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec - external call is intentional in tests
        status = resp.getcode() or 0
        resp_headers = {k: v for k, v in resp.headers.items()}
        content = resp.read()
        return status, resp_headers, content


def print_section(title: str) -> None:
    bar = "=" * max(8, len(title))
    print(f"\n{bar}\n{title}\n{bar}")


def exit_with_error(message: str) -> None:
    print(f"{RED}ERROR: {message}{RESET}", file=sys.stderr)
    sys.exit(1)


def print_error(message: str) -> None:
    """Print an error message in red to stderr without exiting."""
    print(f"{RED}{message}{RESET}", file=sys.stderr)
