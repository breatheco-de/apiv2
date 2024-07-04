import serpy
from django.db.models import QuerySet

from capyc.rest_framework.exceptions import ValidationException

from .datetime_integer_field import DatetimeIntegerField
from .field import Field
from .many_to_many_field import ManyToManyField
from .method_field import MethodField

__all__ = ["Serializer"]

SERPY_FIELDS = [
    Field,
    MethodField,
    DatetimeIntegerField,
    serpy.Field,
    serpy.MethodField,
]


class Serializer(serpy.Serializer):
    """
    This is a wrapper of serpy.Serializer, read the serpy's documentation.

    Extra features:
    - `select` is a list of non-required fields.
    - Avoid unnecesary queries by using `select_related` and `prefetch_related` automatically.
    """

    _select_related: set
    _prefetch_related: set
    _loaded: bool

    def __new__(cls, *args, **kwargs):

        # fix it
        cls._select_related = set()
        cls._prefetch_related = set()
        cls._loaded = False

        return super().__new__(cls)

    def __init__(self, *args, **kwargs):
        kwargs.pop("select", "")
        # select = kwargs.pop('select', '')
        # if select:
        #     self._custom_select(select)

        if "context" in kwargs:
            self.context = kwargs["context"]

        # fix it
        # self.__class__._select_related = set()
        # self.__class__._prefetch_related = set()
        # self.__class__._loaded = False

        super().__init__(*args, **kwargs)

    def _custom_select(self, include):
        include = [x for x in include.split(",") if x]

        for include_field in include:
            if not hasattr(self, include_field):
                raise ValidationException(f"The field {include_field} is not defined in the serializer")

            attr = getattr(self, include_field)
            if isinstance(attr, Field):
                setattr(self, include_field, serpy.Field())
                continue

            method_field = f"get_{include_field}"

            if isinstance(attr, MethodField) and hasattr(self, method_field) and callable(getattr(self, method_field)):
                setattr(self, include_field, serpy.MethodField())
                continue

            raise ValidationException(f"The field {include_field} is not a allowed field or is bad configured")

    def _load_ref(self):
        if self._loaded:
            return self.__class__._select_related, self.__class__._prefetch_related

        for key in self._field_map:

            if self._field_map[key].__class__ not in SERPY_FIELDS:

                self._field_map[key].child = True

                if self._field_map[key].__class__ == ManyToManyField:
                    self.__class__._prefetch_related.add(self._field_map[key].real_attr)

                elif self._field_map[key].many:
                    self.__class__._prefetch_related.add(key)

                else:
                    self.__class__._prefetch_related.add(key)

                if self._field_map[key].__class__ == ManyToManyField:
                    serializer = self._field_map[key].serializer

                    if not (
                        hasattr(self._field_map[key].serializer.__class__, "_select_related")
                        ^ hasattr(self._field_map[key].serializer.__class__, "_prefetch_related")
                    ):
                        select_related, prefetch_related = serializer._load_ref()
                    else:
                        select_related = self._field_map[key].serializer.__class__._select_related
                        prefetch_related = self._field_map[key].serializer.__class__._prefetch_related

                    select_related, prefetch_related = serializer._load_ref()

                else:
                    if not (
                        hasattr(self._field_map[key].__class__, "_select_related")
                        ^ hasattr(self._field_map[key].__class__, "_prefetch_related")
                    ):
                        select_related, prefetch_related = self._field_map[key]._load_ref()
                    else:
                        select_related = self._field_map[key].__class__._select_related
                        prefetch_related = self._field_map[key].__class__._prefetch_related

                for x in select_related:
                    self.__class__._select_related.add(f"{key}__{x}")

                for x in prefetch_related:
                    self.__class__._prefetch_related.add(f"{key}__{x}")

        self._loaded = True

        return self.__class__._select_related, self.__class__._prefetch_related

    @property
    def data(self):

        if not self.__class__._loaded:
            self._load_ref()

        if self.many and isinstance(self.instance, QuerySet) and not hasattr(self, "child"):
            self.instance = self.instance.select_related(*self.__class__._select_related).prefetch_related(
                *self.__class__._prefetch_related
            )

        data = super().data
        return data
