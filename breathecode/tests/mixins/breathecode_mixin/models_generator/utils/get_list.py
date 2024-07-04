from typing import Any

__all__ = ["get_list"]


def get_list(attr: Any) -> bool:
    if isinstance(attr, list):
        return attr

    return [attr]
