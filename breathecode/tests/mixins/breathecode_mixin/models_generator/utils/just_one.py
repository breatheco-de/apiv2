from typing import Any

__all__ = ["just_one"]


def just_one(attr: Any) -> bool:
    is_list = isinstance(attr, list)

    if attr and is_list:
        return attr[0]

    if is_list:
        return None

    return attr
