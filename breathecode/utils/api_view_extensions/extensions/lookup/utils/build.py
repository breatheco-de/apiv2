from typing import Any
from breathecode.utils.api_view_extensions.extensions.lookup.fields.generic.lookup_field import LookupField
from breathecode.utils.api_view_extensions.extensions.lookup.utils.build_lookups import build_lookups


# this keep here to become it public in test environment
def build(model, fields: dict, custom_fields: dict = dict(),
          overwrite: dict = dict()) -> dict[str, LookupField]:

    kwargs = {}
    for key in fields:
        kwargs[key] = tuple(fields[key])

    alias = [(y, x) for x, y in overwrite.items()]

    # get cache of lookups
    return build_lookups(model, frozenset(custom_fields.items()), frozenset(alias), **kwargs)
