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


class IntegerField:

    def validator(self, lang, value):
        try:
            return int(value)

        except ValidationException:
            raise ValidationException(
                translation(lang,
                            en=f'{self.field} must be an integer',
                            es=f'{self.field} debe ser un entero',
                            slug=f'{self.field.replace("_", "-")}-must-be-an-integer'))

    def append_prefix(self, prefix):
        self.prefix = prefix

    def value(self, value):
        return Q(**{self.prefix + self.lookup + self.suffix: value})

    def __init__(self, model, field, mode: Mode):
        self.model = model
        self.prefix = ''
        self.suffix = ''
        self.field = field
        self.mode = mode

    def set_lookup(self):
        self.lookup = f'{self.prefix}{self.field}'

        if self.mode == Mode.EXACT:
            self.suffix = ''

        elif self.mode == Mode.IN:
            self.suffix = '__in'

        elif self.mode == Mode.GREATER_THAN:
            self.suffix = '__gt'

        elif self.mode == Mode.GREATER_THAN_EQUAL:
            self.suffix = '__gte'

        elif self.mode == Mode.LOWER_THAN:
            self.suffix = '__lt'

        elif self.mode == Mode.LOWER_THAN_EQUAL:
            self.suffix = '__lte'

    def handlers(self):

        if self.mode not in [
                Mode.EXACT, Mode.IN, Mode.GREATER_THAN, Mode.GREATER_THAN_EQUAL, Mode.LOWER_THAN,
                Mode.LOWER_THAN_EQUAL
        ]:
            raise ValidationException(f'Mode {self.mode} is not supported for integer field {self.field}')

        self.set_lookup()
        return self.value, self.validator
