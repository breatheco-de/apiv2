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

        extra = {}
        for key in fields:
            extra[key] = tuple(fields[key])

        alias2 = [(y, x) for x, y in overwrite.items()]

        # get cache of lookups
        lookups = build_lookups(model, frozenset(custom_fields.items()), frozenset(alias2), **extra)

        alias = dict(overwrite)

        for key in self._request.GET:
            name = alias.get(key, key)

            if key in custom_fields:
                value = self._request.GET.get(key)
                result &= custom_fields[key](value)

            if name in lookups:

                field, validator = lookups[name].handlers()
                value = self._request.GET.get(key)

                if validator is not None:
                    value = validator(lang, value)

                result &= field(value)

        return result

    def _can_modify_queryset(self) -> bool:
        return False

    def _can_modify_response(self) -> bool:
        return False

    def _instance_name(self) -> Optional[str]:
        return 'lookup'
