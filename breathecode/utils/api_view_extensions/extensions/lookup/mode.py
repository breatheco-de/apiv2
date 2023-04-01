from enum import Enum, auto


class Mode(Enum):
    # math
    EXACT = auto()
    GREATER_THAN = auto()
    LOWER_THAN = auto()
    GREATER_THAN_EQUAL = auto()
    LOWER_THAN_EQUAL = auto()

    # string
    CONTAINS = auto()
    INSENSITIVE_CONTAINS = auto()
    INSENSITIVE_EXACT = auto()
    STARTS_WITH = auto()
    ENDS_WITH = auto()

    # array
    CONTAINED_BY = auto()
    HAS_KEY = auto()
    HAS_KEYS = auto()
    HAS_ANY_KEYS = auto()
    IN = auto()

    # boolean
    IS_TRUE = auto()
    IS_FALSE = auto()

    # null
    IS_NULL = auto()
    IS_NOT_NONE = auto()

    # date
    YEAR = auto()
    MONTH = auto()
    DAY = auto()
    HOUR = auto()
    MINUTE = auto()

    # custom
    ID = auto()
