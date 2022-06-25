from enum import IntEnum

__all__ = ['ResponseOrder']


class ResponseOrder(IntEnum):
    PAGINATION = 0  # keep before than lastest number
    CACHE = 1  # keep as lastest number
