import random
from typing import Any

from django.db.models import Q
from breathecode.utils.api_view_extensions.extensions.lookup.fields.generic.lookup_field import LookupField

from breathecode.utils.validation_exception import ValidationException
from ..mode import Mode

__all__ = ['LookupExtension']


class IDField(LookupField):

    def generator(self) -> str:
        is_int = bool(random.randbytes(1))

        if is_int:
            return f'{random.randint(0, 100000000000000000)}'

        return self.fake.slug()

    def validator(self, _: Any, value: str):
        if value.isnumeric() and self.model._meta.pk.name == 'id':
            return int(value)

        return value

    def append_prefix(self, prefix):
        self.prefix = prefix + self.prefix

    def value(self, value):
        f = self.field
        if f != '':
            f += '__'

        if isinstance(value, int):
            return Q(**{self.prefix + f'{f}pk': value})

        if self.model._meta.pk.name != 'id':
            return Q(**{self.prefix + f'{f}pk': value})

        return Q(**{self.prefix + f'{f}slug': value})

    def __init__(self, model, field, mode: Mode):
        super().__init__(model, field, mode)
        self.model = model
        self.suffix = ''
        self.prefix = ''
        self.field = field
        self.mode = mode

    def set_lookup(self):
        if self.mode not in [Mode.ID]:
            raise ValidationException(f'Mode {self.mode} is not supported for id field {self.field}')

        self.lookup = f'{self.prefix}{self.field}'

    def handlers(self):
        self.set_lookup()
        return self.value, self.validator, self.generator
