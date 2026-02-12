"""
Reusable helpers for hierarchical JSON settings/features.

IMPORTANT:
This module intentionally lives outside `breathecode.utils` to avoid importing
`breathecode/utils/__init__.py` during Django model import time (which can
trigger circular imports via decorators).
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


def deep_merge_dict(default: dict, override: dict) -> dict:
    """
    Deep merge two dictionaries, with override taking precedence.

    - If a key exists in both and both values are dicts, merge recursively.
    - Otherwise, override replaces default.
    """

    result = default.copy()
    for key, value in (override or {}).items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge_dict(result[key], value)
        else:
            result[key] = value

    return result


def iter_leaf_paths(data: dict, prefix: str = ""):
    """
    Yield dot-paths for leaf values in a nested dict.

    Only traverses dicts; any non-dict value (including lists) is treated as a leaf.
    """

    if not isinstance(data, dict):
        return

    for key, value in data.items():
        path = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, dict):
            yield from iter_leaf_paths(value, prefix=path)
        else:
            yield path


def is_path_allowed(changed_path: str, allowed_paths: list[str]) -> bool:
    """
    Determine if a changed dot-path is allowed by a list of allowed dot-paths.

    A path is allowed if:
    - It matches exactly an allowed path, OR
    - It is a descendant of an allowed path (prefix match).
    """

    for allowed in allowed_paths or []:
        if changed_path == allowed:
            return True

        if allowed and changed_path.startswith(allowed + "."):
            return True

    return False


def _get_by_parts(data: dict, parts: list[str]):
    current = data
    for part in parts:
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _set_by_parts(target: dict, parts: list[str], value):
    current = target
    for part in parts[:-1]:
        if part not in current or not isinstance(current[part], dict):
            current[part] = {}
        current = current[part]

    if parts:
        current[parts[-1]] = value


def extract_allowed_tree(data: dict, allowed_paths: list[str]) -> dict:
    """
    Extract a subset of `data` containing only the keys/paths allowed.
    """

    if not isinstance(data, dict):
        return {}

    result: dict = {}
    for allowed in allowed_paths or []:
        if not isinstance(allowed, str) or not allowed:
            continue

        parts = allowed.split(".")
        value = _get_by_parts(data, parts)
        if value is None:
            continue

        _set_by_parts(result, parts, value)

    return result


class ConfigurableSettingsMixin:
    """
    Mixin to provide overridable settings/features with defaults + parent inheritance + overrides.
    """

    SETTINGS_FIELD: str = "settings"
    DEFAULT_SETTINGS: Any = dict
    PARENT_LOOKUP: str | None = None

    def _get_default_settings(self) -> dict:
        default = self.DEFAULT_SETTINGS
        if callable(default):
            default = default()

        if default is None:
            return {}

        if not isinstance(default, dict):
            raise TypeError("DEFAULT_SETTINGS must be a dict or a callable returning a dict")

        return deepcopy(default)

    def _get_raw_settings(self) -> dict:
        raw = getattr(self, self.SETTINGS_FIELD, None)
        if raw is None:
            return {}

        if not isinstance(raw, dict):
            return {}

        return raw

    def _get_parent_chain(self) -> list:
        if not self.PARENT_LOOKUP:
            return []

        chain = []
        current = self
        for part in self.PARENT_LOOKUP.split("__"):
            current = getattr(current, part, None)
            if current is None:
                break
            chain.append(current)

        return chain

    def get_effective_settings(self) -> dict:
        base = self._get_default_settings()

        chain = self._get_parent_chain()
        for parent in reversed(chain):
            if hasattr(parent, "get_effective_settings"):
                base = deep_merge_dict(base, parent.get_effective_settings())

        base = deep_merge_dict(base, self._get_raw_settings())
        return base

    def get_setting(self, key: str, default=None):
        return self.get_effective_settings().get(key, default)


