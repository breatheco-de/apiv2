from typing import Any
from breathecode.utils.api_view_extensions.extensions.lookup.utils.build import build
from django.db.models import Q


def lookup_generator(model, fields: dict, custom_fields: dict = dict(),
                     overwrite: dict = dict()) -> dict[str, Any]:

    lookups = build(model, fields, custom_fields, overwrite)
    querystring = {}
    query = Q()

    result = {}

    overwrite = dict([(y, x) for x, y in overwrite.items()])

    for key in lookups:
        get_value, validator, generator = lookups[key].handlers()
        k = overwrite.get(key, key)
        querystring[k] = generator()

        if key in custom_fields:
            value = querystring.get(key)
            result[key] = custom_fields[key](value)
            continue

        value = querystring[k]

        if validator is not None:
            value = validator('en', value)

        result[k] = get_value(value)

    for key in sorted([x for x in result]):
        query &= result[key]

    return querystring, query
