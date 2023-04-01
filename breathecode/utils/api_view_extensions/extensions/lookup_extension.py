from typing import Any, Optional

from breathecode.utils.api_view_extensions.extension_base import ExtensionBase
from breathecode.utils.api_view_extensions.extensions.lookup.utils.build_lookups import build_lookups

from django.db.models import Q
from .lookup.mode import Mode

__all__ = ['LookupExtension']


class LookupExtension(ExtensionBase):
    mode = Mode

    def __init__(self, **kwargs) -> None:
        ...

    def build(self, model, lang: str, fields: dict, custom_fields: dict = dict(),
              overwrite: dict = dict()) -> tuple[tuple, dict]:
        result = Q()

        kwargs = {}
        for key in fields:
            kwargs[key] = tuple(fields[key])

        alias = [(y, x) for x, y in overwrite.items()]

        # get cache of lookups
        lookups = build_lookups(model, frozenset(custom_fields.items()), frozenset(alias), **kwargs)

        for key in self._request.GET:
            name = overwrite.get(key, key)

            if key in custom_fields:
                value = self._request.GET.get(key)
                result &= custom_fields[key](value)
                continue

            if name in lookups:

                get_value, validator = lookups[name].handlers()
                value = self._request.GET.get(key)

                if validator is not None:
                    value = validator(lang, value)

                result &= get_value(value)

        return result

    def _can_modify_queryset(self) -> bool:
        return False

    def _can_modify_response(self) -> bool:
        return False

    def _instance_name(self) -> Optional[str]:
        return 'lookup'
