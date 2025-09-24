"""CLI dispatcher for functional tests.

Usage:
    python -m scripts.fttests list
    python -m scripts.fttests <feature>

Each feature is a subpackage under `scripts/fttests/` exporting:
    - check_dependencies() -> None  # raises AssertionError or exits on failure
    - run() -> None                 # raises AssertionError or exits on failure
"""

from __future__ import annotations

import importlib
import os
import pkgutil
import sys
from types import ModuleType


PKG_NAME = __package__ or "scripts.fttests"


def _discover_features() -> list[str]:
    base_dir = os.path.dirname(__file__)
    names = []
    for m in pkgutil.iter_modules([base_dir]):
        if m.ispkg and not m.name.startswith("_"):
            names.append(m.name)
    names.sort()
    return names


def _print_usage(features: list[str]) -> None:
    print(
        "Usage: python -m scripts.fttests <feature>\n"
        "       python -m scripts.fttests list\n\n"
        "Available features:\n  - " + "\n  - ".join(features)
    )


def _load_feature(name: str) -> ModuleType:
    try:
        return importlib.import_module(f"{PKG_NAME}.{name}")
    except ModuleNotFoundError as exc:
        print(f"Unknown feature '{name}'. Use 'list' to see available features.", file=sys.stderr)
        raise SystemExit(1) from exc


def _ensure_contract(mod: ModuleType) -> None:
    missing = [attr for attr in ("check_dependencies", "run") if not hasattr(mod, attr)]
    if missing:
        print(
            f"Feature module '{mod.__name__}' is missing required symbols: {', '.join(missing)}",
            file=sys.stderr,
        )
        raise SystemExit(1)


def main(argv: list[str]) -> int:
    features = _discover_features()

    if not argv or argv[0] in {"-h", "--help", "help"}:
        _print_usage(features)
        return 0

    if argv[0] in {"list", "ls"}:
        for name in features:
            print(name)
        return 0

    feature_name = argv[0]
    mod = _load_feature(feature_name)
    _ensure_contract(mod)

    try:
        print(f"[fttests] Running dependencies check for '{feature_name}'...")
        mod.check_dependencies()
        print(f"[fttests] Dependencies OK. Running tests for '{feature_name}'...\n")
        mod.run()
    except AssertionError as exc:
        print(f"Assertion failed: {exc}", file=sys.stderr)
        return 1
    except SystemExit as exc:
        # Allow feature to control exit code when explicitly exiting
        return int(exc.code) if isinstance(exc.code, int) else 1
    except Exception as exc:  # noqa: BLE001 - surface any unexpected failure
        print(f"Unexpected error: {exc}", file=sys.stderr)
        return 1

    print(f"\n[fttests] Feature '{feature_name}' finished successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
