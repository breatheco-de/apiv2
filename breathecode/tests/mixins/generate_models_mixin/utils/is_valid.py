from typing import Any

__all__ = ["is_valid"]


def is_valid(attr: Any) -> bool:
    if attr or isinstance(attr, dict):
        return True

    return False
