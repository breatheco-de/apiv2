from typing import Optional

from breathecode.utils.api_view_extensions.extension_base import ExtensionBase
from breathecode.utils.api_view_extensions.extensions.lookup.utils.build import build

from django.db.models import Q
from .lookup.mode import Mode

__all__ = ['LookupExtension']


def compile_lookup(
    querystring: dict, model, lang: str, fields: dict, custom_fields: dict = dict(),
    overwrite: dict = dict()) -> tuple[tuple, dict]:

    query = Q()
    lookups = build(model, fields, custom_fields, overwrite)
    result = {}

    for key in querystring:
        name = overwrite.get(key, key)

        if key in custom_fields:
            value = querystring.get(key)
            result[key] = custom_fields[key](value)
            continue

        if name in lookups:

            get_value, validator, _ = lookups[name].handlers()
            value = querystring.get(key)

            if validator is not None:
                value = validator(lang, value)

            result[key] = get_value(value)

    for key in sorted([x for x in result]):
        query &= result[key]

    return query


class LookupExtension(ExtensionBase):
    mode = Mode

    def __init__(self, **kwargs) -> None:
        ...

    def build(self, model, lang: str, fields: dict, custom_fields: dict = dict(),
              overwrite: dict = dict()) -> tuple[tuple, dict]:

        return compile_lookup(dict([(x, self._request.GET.get(x)) for x in self._request.GET]),
                              model,
                              lang,
                              fields=fields,
                              custom_fields=custom_fields,
                              overwrite=overwrite)

    def _can_modify_queryset(self) -> bool:
        return False

    def _can_modify_response(self) -> bool:
        return False

    def _instance_name(self) -> Optional[str]:
        return 'lookup'
