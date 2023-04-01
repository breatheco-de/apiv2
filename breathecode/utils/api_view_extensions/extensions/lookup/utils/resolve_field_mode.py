from typing import Optional
from breathecode.utils.api_view_extensions.extensions.lookup.mode import Mode


def resolve_field_mode(name,
                       id: Optional[tuple] = None,
                       exact: Optional[tuple] = None,
                       gt: Optional[tuple] = None,
                       gte: Optional[tuple] = None,
                       lt: Optional[tuple] = None,
                       lte: Optional[tuple] = None,
                       is_null: Optional[tuple] = None):
    mode = None

    if exact and name in list(exact):
        mode = Mode.EXACT

    elif gt and name in list(gt):
        mode = Mode.GREATER_THAN

    elif gte and name in list(gte):
        mode = Mode.GREATER_THAN_EQUAL

    elif lt and name in list(lt):
        mode = Mode.LOWER_THAN

    elif lte and name in list(lte):
        mode = Mode.LOWER_THAN_EQUAL

    elif id and name in list(id):
        mode = Mode.ID

    elif is_null and name in list(is_null):
        mode = Mode.IS_NULL

    return mode
