from datetime import datetime
from enum import Enum, auto
from typing import Any, Optional

from breathecode.utils.api_view_extensions.extension_base import ExtensionBase
from django.core.handlers.wsgi import WSGIRequest
from django.db.models.fields.related_descriptors import (ReverseManyToOneDescriptor, ManyToManyDescriptor,
                                                         ForwardManyToOneDescriptor)
from functools import cache

from breathecode.utils.i18n import translation
from django.db import models
from django.db.models import Q

from breathecode.utils.validation_exception import ValidationException
from ..mode import Mode

__all__ = ['LookupExtension']


class IDField:

    def validator(self, _: Any, value: str):
        if value.isnumeric() and self.model._meta.pk.name == 'id':
            return int(value)

        return value

    def append_prefix(self, prefix):
        self.prefix = prefix

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
        self.model = model
        self.suffix = ''
        self.prefix = ''
        self.field = field
        self.mode = mode

    def set_lookup(self):
        self.lookup = f'{self.prefix}{self.field}'

        if self.mode not in [Mode.ID]:
            raise ValidationException(f'Mode {self.mode} is not supported for id field {self.field}')

    def handlers(self):
        self.set_lookup()
        return self.value, self.validator
