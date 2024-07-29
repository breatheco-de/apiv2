from functools import cache
from typing import Any, Callable, Optional

from django.db.models import Q
from django.utils import dateparse

from breathecode.utils.api_view_extensions.extension_base import ExtensionBase
from breathecode.utils.i18n import translation
from capyc.rest_framework.exceptions import ValidationException

__all__ = ["LookupExtension"]


class Field:

    @staticmethod
    def id(lang: str, key: str, value: str, alias=None) -> Q:
        if not value.isnumeric():
            raise ValidationException(
                translation(
                    lang,
                    en="ID must be numeric",
                    es="El ID debe ser numérico",
                    pt="O ID deve ser numérico",
                    slug="id-must-be-numeric",
                )
            )

        return Q(**{f"{key}__pk": int(value)})

    @staticmethod
    def integer(mode: str) -> Callable[[str, str, str], Q]:

        def handler(lang: str, key: str, value: str, alias=None) -> Q:
            if not value.isnumeric():
                el = alias or key
                raise ValidationException(
                    translation(
                        lang,
                        en=f"{el} must be numeric",
                        es=f"El {el} debe ser numérico",
                        pt=f"O {el} deve ser numérico",
                        slug=f'{el.replace("_", "-")}-must-be-numeric',
                    )
                )

            return Q(**{f"{key}__{mode}": int(value)})

        return handler

    @staticmethod
    def slug(lang: str, key: str, value: str, alias=None) -> Q:
        if value.isnumeric():
            return Q(**{f"{key}__pk": int(value)})

        return Q(**{f"{key}__slug": value})

    @staticmethod
    def string(mode: str) -> Callable[[str, str, str], Q]:

        def handler(lang: str, key: str, value: str, alias=None) -> str:
            param = value
            if mode == "in":
                param = param.split(",") if param is not None else []
            return Q(**{f"{key}__{mode}": param})

        return handler

    @staticmethod
    def datetime(mode: str) -> Callable[[str, str, str], Q]:

        def handler(lang: str, key: str, value: str, alias=None) -> Q:
            if mode == "year" or mode == "month" or mode == "day" or mode == "hour" or mode == "minute":

                if not value.isnumeric():
                    el = (alias or key).replace("_", "-")

                    raise ValidationException(
                        translation(
                            lang,
                            en=f"{el} must be numeric",
                            es=f"El {el} debe ser numérico",
                            pt=f"O {el} deve ser numérico",
                            slug=f'{el.replace("_", "-")}-must-be-numeric',
                        )
                    )

                return Q(**{f"{key}__{mode}": int(value)})

            if mode == "isnull":
                return Q(**{f"{key}__{mode}": value == "true"})

            if not value or not (d := dateparse.parse_datetime(value)):
                el = alias or key
                raise ValidationException(
                    translation(
                        lang,
                        en=f"{el} must be a datetime",
                        es=f"{el} debe ser un datetime",
                        slug=f'{el.replace("_", "-")}-must-be-a-datetime',
                    )
                )

            return Q(**{f"{key}__{mode}": d})

        return handler

    @staticmethod
    def bool(mode: str) -> Callable[[str, str, str], Q]:

        def handler(lang: str, key: str, value: str, alias=None) -> Q:
            return Q(**{f"{key}__{mode}": value == "true"})

        return handler


class CompileLookupField:

    @staticmethod
    def string(strings: str) -> dict[str, Callable[[str, str, str, Optional[str]], Q]]:
        lookup = {}

        for key in strings.get("exact", tuple()):
            lookup[key] = Field.string("exact")

        for key in strings.get("in", tuple()):
            lookup[key] = Field.string("in")

        for key in strings.get("contains", tuple()):
            lookup[key] = Field.string("contains")

        for key in strings.get("icontains", tuple()):
            lookup[key] = Field.string("icontains")

        for key in strings.get("iexact", tuple()):
            lookup[key] = Field.string("iexact")

        for key in strings.get("startswith", tuple()):
            lookup[key] = Field.string("startswith")

        for key in strings.get("endswith", tuple()):
            lookup[key] = Field.string("endswith")

        return lookup

    @staticmethod
    def integer(strings: str) -> dict[str, Callable[[str, str, str, Optional[str]], Q]]:
        lookup = {}

        for key in strings.get("exact", tuple()):
            lookup[key] = Field.integer("exact")

        for key in strings.get("in", tuple()):
            lookup[key] = Field.integer("in")

        for key in strings.get("gt", tuple()):
            lookup[key] = Field.integer("gt")

        for key in strings.get("gte", tuple()):
            lookup[key] = Field.integer("gte")

        for key in strings.get("lt", tuple()):
            lookup[key] = Field.integer("lte")

        return lookup

    @staticmethod
    def datetime(strings: str) -> dict[str, Callable[[str, str, str, Optional[str]], Q]]:
        lookup = {}

        for key in strings.get("exact", tuple()):
            lookup[key] = Field.datetime("exact")

        for key in strings.get("in", tuple()):
            lookup[key] = Field.datetime("in")

        for key in strings.get("gt", tuple()):
            lookup[key] = Field.datetime("gt")

        for key in strings.get("gte", tuple()):
            lookup[key] = Field.datetime("gte")

        for key in strings.get("lt", tuple()):
            lookup[key] = Field.datetime("lte")

        for key in strings.get("year", tuple()):
            lookup[key] = Field.datetime("year")

        for key in strings.get("month", tuple()):
            lookup[key] = Field.datetime("month")

        for key in strings.get("day", tuple()):
            lookup[key] = Field.datetime("day")

        for key in strings.get("hour", tuple()):
            lookup[key] = Field.datetime("hour")

        for key in strings.get("minute", tuple()):
            lookup[key] = Field.datetime("minute")

        for key in strings.get("isnull", tuple()):
            lookup[key] = Field.datetime("isnull")

        return lookup

    @staticmethod
    def bool(strings: str) -> dict[str, Callable[[str, str, str, Optional[str]], Q]]:
        lookup = {}

        for key in strings.get("exact", tuple()):
            lookup[key] = Field.bool("exact")

        return lookup


# keeps it here to spy the arguments passed
@cache
def compile_lookup(
    ids: tuple, slugs: tuple, ints: frozenset, strings: frozenset, datetimes: frozenset, bools: frozenset
) -> tuple[tuple, dict]:
    """Compile the available lookup fields once."""

    strings = dict(strings)
    lookup = {}

    for key in ids:
        if key == "":
            lookup.update(CompileLookupField.integer({"exact": ("id",)}))
            continue

        lookup[key] = Field.id

    for key in slugs:
        if key == "":
            lookup.update(CompileLookupField.integer({"exact": ("id",)}))
            lookup.update(CompileLookupField.string({"exact": ("slug",)}))
            continue

        lookup[key] = Field.slug

    lookup.update(CompileLookupField.string(dict(strings)))
    lookup.update(CompileLookupField.integer(dict(ints)))
    lookup.update(CompileLookupField.datetime(dict(datetimes)))
    lookup.update(CompileLookupField.bool(dict(bools)))

    return lookup


class LookupExtension(ExtensionBase):

    def __init__(self, **kwargs) -> None: ...

    def _build_lookup(
        self,
        lang: str,
        lookup: dict[str, Callable[[str, str, str, Optional[str]], Q]],
        querystring: dict[str, Any],
        custom_fields: Optional[dict] = None,
        overwrite: Optional[dict] = None,
    ) -> tuple[tuple, dict]:
        if custom_fields is None:
            custom_fields = {}

        if overwrite is None:
            overwrite = {}

        query = Q()
        lookup = lookup.copy()

        for key in querystring:
            name = overwrite.get(key, key)

            if name in custom_fields:
                value = querystring.get(key)
                query &= custom_fields[name](value)
                continue

            if name in lookup:
                value = querystring.get(key)
                query &= lookup[name](lang, name, value, name)

        return query

    def _to_frozenset(self, value: Optional[dict]) -> frozenset:
        result = {}
        if value is None:
            return frozenset()

        if not isinstance(value, dict):
            raise ValidationException("value must be a dict", code=500)

        for key in value:
            if not isinstance(value[key], tuple):
                result[key] = tuple(value[key])

            else:
                result[key] = value[key]

        return frozenset(result.items())

    def _fixer(self, querystring: dict[str, str], fix) -> dict[str, str]:
        return querystring

    def build(self, lang: str, overwrite: Optional[dict] = None, **kwargs: dict | tuple) -> tuple[tuple, dict]:
        if overwrite is None:
            overwrite = {}

        # foreign
        ids = kwargs.get("ids", tuple())
        slugs = kwargs.get("slugs", tuple())

        # fields
        ints = kwargs.get("ints", dict())
        strings = kwargs.get("strings", dict())
        datetimes = kwargs.get("datetimes", dict())
        bools = kwargs.get("bools", dict())

        # opts
        custom_fields = kwargs.get("custom_fields", dict())
        fix = kwargs.get("custom_fields", dict())

        # serialize foreign
        ids = tuple(ids)
        slugs = tuple(slugs)

        # serialize fields
        ints = self._to_frozenset(ints)
        bools = self._to_frozenset(bools)
        datetimes = self._to_frozenset(datetimes)
        strings = self._to_frozenset(strings)

        # request
        querystring = dict([(x, self._request.GET.get(x)) for x in self._request.GET])

        lookup = compile_lookup(ids=ids, slugs=slugs, ints=ints, strings=strings, datetimes=datetimes, bools=bools)

        if fix:
            querystring = self._fixer(querystring, fix)

        return self._build_lookup(lang, lookup, querystring, custom_fields, overwrite)

    def _can_modify_queryset(self) -> bool:
        return False

    def _can_modify_response(self) -> bool:
        return False

    def _instance_name(self) -> Optional[str]:
        return "lookup"
