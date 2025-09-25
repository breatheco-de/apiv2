"""CLI dispatcher for functional tests.

Usage:
    python -m scripts.fttests list
    python -m scripts.fttests <feature>

Features are subpackages under `scripts/fttests/`.
Optionally they can export:
    - check_dependencies() -> None  # if present, it will be called before tests

Test collection is handled by this runner:
    - Any function named ``test_*`` within the feature package (its __init__.py and
      direct submodules) will be discovered and executed.
    - If no tests are found and the feature defines ``run()``, the runner will
      delegate to it as a fallback for legacy features.
"""

from __future__ import annotations

import importlib
import inspect
import os
import pkgutil
import sys
from types import ModuleType

# ANSI colors
RED = "\033[31m"
RESET = "\033[0m"


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
        print(f"{RED}Unknown feature '{name}'. Use 'list' to see available features.{RESET}", file=sys.stderr)
        raise SystemExit(1) from exc


def _ensure_contract(mod: ModuleType) -> None:
    # No hard requirements: discovery is centralized and check_dependencies is optional.
    return None


def _discover_tests_for_feature(feature_mod: ModuleType) -> list[tuple[str, callable]]:
    """Discover all test_* functions within the given feature package.

    Returns a list of (fullname, function) tuples.
    """
    tests: list[tuple[str, callable]] = []

    # include the package's own module
    tests.extend(_discover_module_tests(feature_mod))

    # include direct submodules (non-underscore files)
    for mod in _iter_feature_modules(feature_mod):
        tests.extend(_discover_module_tests(mod))

    return tests


def _discover_module_tests(mod: ModuleType) -> list[tuple[str, callable]]:
    """Discover test_* in definition order.

    inspect.getmembers sorts by name; instead iterate mod.__dict__ to preserve
    definition order (insertion-ordered in modern Python).
    """
    found: list[tuple[str, callable]] = []
    for name, obj in mod.__dict__.items():
        if (
            isinstance(name, str)
            and name.startswith("test_")
            and inspect.isfunction(obj)
            and getattr(obj, "__module__", None) == mod.__name__
        ):
            found.append((f"{mod.__name__}.{name}", obj))
    return found


def _iter_feature_modules(feature_mod: ModuleType):
    pkg = feature_mod.__name__
    try:
        pkg_path = feature_mod.__path__  # type: ignore[attr-defined]
    except AttributeError:
        return []  # not a package

    modules = []
    for m in pkgutil.iter_modules(list(pkg_path)):
        if m.ispkg or m.name.startswith("_"):
            continue
        modules.append(importlib.import_module(f"{pkg}.{m.name}"))
    return modules


def _format_test_name(fullname: str, feature: str) -> str:
    """Format a fully-qualified test name into 'feature -> module -> test'.

    Example:
      'scripts.fttests.subscription_seats.smoke.test_x' ->
      'subscription_seats -> smoke -> test_x'
    """
    parts = fullname.split(".")
    try:
        idx = parts.index(feature)
    except ValueError:
        # Fallback: try to strip the package prefix if present
        prefix = f"{PKG_NAME}."
        if fullname.startswith(prefix):
            trimmed = fullname[len(prefix) :]
            parts = trimmed.split(".")
            # Recompute feature index (should be 0 now)
            feature = parts[0] if parts else feature
            module_parts = parts[1:-1]
            func = parts[-1] if parts else fullname
            return feature + (" -> " + " -> ".join(module_parts) if module_parts else "") + f" -> {func}"

    module_parts = parts[idx + 1 : -1]
    func = parts[-1]
    return feature + (" -> " + " -> ".join(module_parts) if module_parts else "") + f" -> {func}"


def _format_module_name(module_fullname: str, feature: str) -> str:
    """Format a fully-qualified module name into 'feature -> module'."""
    parts = module_fullname.split(".")
    try:
        idx = parts.index(feature)
    except ValueError:
        prefix = f"{PKG_NAME}."
        if module_fullname.startswith(prefix):
            trimmed = module_fullname[len(prefix) :]
            parts = trimmed.split(".")
            feature = parts[0] if parts else feature
            module_parts = parts[1:]
            return feature + (" -> " + " -> ".join(module_parts) if module_parts else "")
        return module_fullname

    module_parts = parts[idx + 1 :]
    return feature + (" -> " + " -> ".join(module_parts) if module_parts else "")


def _discover_tests_grouped(feature_mod: ModuleType) -> list[tuple[ModuleType, list[tuple[str, callable]]]]:
    """Discover tests grouped by module.

    Returns a list of tuples: (module, [(fullname, func), ...]). Includes modules
    that define a setup()/teardown() even if they have no test_* functions.
    """
    groups: list[tuple[ModuleType, list[tuple[str, callable]]]] = []
    modules = [feature_mod] + _iter_feature_modules(feature_mod)
    for mod in modules:
        tests = _discover_module_tests(mod)
        if tests or hasattr(mod, "setup") or hasattr(mod, "teardown"):
            groups.append((mod, tests))
    return groups


def _build_call_kwargs(func: callable, context: dict) -> dict:
    """Build kwargs for calling a function from a shared context.

    - If function accepts **kwargs, pass the entire context.
    - Else, pass only the keys that match the function's named parameters.
    """
    try:
        sig = inspect.signature(func)
    except (TypeError, ValueError):
        return {}

    params = sig.parameters
    # Has **kwargs
    if any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values()):
        return dict(context)

    allowed = {
        name
        for name, p in params.items()
        if p.kind
        in (
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        )
    }
    return {k: v for k, v in context.items() if k in allowed}


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
        if hasattr(mod, "check_dependencies"):
            print(f"[fttests] Running dependencies check for '{feature_name}'...")
            mod.check_dependencies()
            print("[fttests] Dependencies OK.\n")
        else:
            print(f"[fttests] No check_dependencies() found for '{feature_name}'. Skipping.\n")

        # Discover tests (grouped by module) in the feature package
        groups = _discover_tests_grouped(mod)
        test_count = sum(len(tests) for _, tests in groups)
        if groups:
            print(f"[fttests] Discovered {test_count} test(s) for '{feature_name}'. Running...\n")
            total = 0
            failures: list[str] = []

            for module_obj, tests in groups:
                module_pretty = _format_module_name(module_obj.__name__, feature_name)
                context: dict = {}

                # Optional setup()
                setup_fn = getattr(module_obj, "setup", None)
                if callable(setup_fn):
                    label = f"{module_pretty} -> setup"
                    print(f"[fttests] SETUP {label}")
                    try:
                        ret = setup_fn(**_build_call_kwargs(setup_fn, context))
                        if isinstance(ret, dict):
                            context.update(ret)
                        print(f"[fttests] OK    {label}")
                    except AssertionError as exc:
                        print(f"{RED}[fttests] FAIL  {label} -> {exc}{RESET}")
                        failures.append(f"{label}: {exc}")
                        # Skip this module's tests and teardown
                        continue
                    except Exception as exc:  # noqa: BLE001
                        print(f"{RED}[fttests] ERROR {label} -> {exc}{RESET}")
                        failures.append(f"{label}: unexpected error: {exc}")
                        continue

                # Run tests in module
                for fullname, func in tests:
                    total += 1
                    pretty = _format_test_name(fullname, feature_name)
                    print(f"[fttests] RUN   {pretty}")
                    try:
                        ret = func(**_build_call_kwargs(func, context))
                        if isinstance(ret, dict):
                            context.update(ret)
                        print("[fttests] OK")
                    except AssertionError as exc:
                        print(f"{RED}[fttests] FAIL    -> {exc}{RESET}")
                        failures.append(f"{pretty}: {exc}")
                    except Exception as exc:  # noqa: BLE001
                        print(f"{RED}[fttests] ERROR -> {exc}{RESET}")
                        failures.append(f"{pretty}: unexpected error: {exc}")

                # Optional teardown()
                teardown_fn = getattr(module_obj, "teardown", None)
                if callable(teardown_fn):
                    label = f"{module_pretty} -> teardown"
                    print(f"[fttests] TEARDOWN {label}")
                    try:
                        teardown_fn(**_build_call_kwargs(teardown_fn, context))
                        print(f"[fttests] OK       {label}")
                    except AssertionError as exc:
                        print(f"{RED}[fttests] FAIL     {label} -> {exc}{RESET}")
                        failures.append(f"{label}: {exc}")
                    except Exception as exc:  # noqa: BLE001
                        print(f"{RED}[fttests] ERROR    {label} -> {exc}{RESET}")
                        failures.append(f"{label}: unexpected error: {exc}")

            print(f"\n[fttests] Ran {total} test(s).")
            if failures:
                print("[fttests] Failures:")
                for msg in failures:
                    print(f" - {msg}")
                return 1
        else:
            # Fallback to legacy feature runner if provided
            if hasattr(mod, "run"):
                print(f"[fttests] No tests found for '{feature_name}'; delegating to feature's run()...\n")
                mod.run()
            else:
                print(f"{RED}Feature '{feature_name}' has no tests and no run() fallback{RESET}", file=sys.stderr)
                return 1
    except AssertionError as exc:
        print(f"{RED}Assertion failed: {exc}{RESET}", file=sys.stderr)
        return 1
    except SystemExit as exc:
        # Allow feature to control exit code when explicitly exiting
        return int(exc.code) if isinstance(exc.code, int) else 1
    except Exception as exc:  # noqa: BLE001 - surface any unexpected failure
        print(f"{RED}Unexpected error: {exc}{RESET}", file=sys.stderr)
        return 1

    print(f"\n[fttests] Feature '{feature_name}' finished successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
