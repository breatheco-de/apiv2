from typing import TypeVar

__all__ = ["AttrDict"]

T = TypeVar("T")


class AttrDict(dict):
    """Support use a dict like a javascript object."""

    def __init__(self, **kwargs: T):
        dict.__init__(self, **kwargs)

    def __setattr__(self, name: str, value: T):
        self[name] = value

    def __getattr__(self, name: str) -> T:
        return self[name]
