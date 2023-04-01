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


class StringField:

    def value(self, value):
        return Q(**{self.prefix + self.lookup + self.suffix: value})

    def append_prefix(self, prefix):
        self.prefix = prefix

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

        elif self.mode == Mode.CONTAINS:
            self.suffix = '__contains'

        elif self.mode == Mode.INSENSITIVE_CONTAINS:
            self.suffix = '__icontains'

        elif self.mode == Mode.INSENSITIVE_EXACT:
            self.suffix = '__iexact'

        elif self.mode == Mode.STARTS_WITH:
            self.suffix = '__startswith'

        elif self.mode == Mode.ENDS_WITH:
            self.suffix = '__endswith'

    def handlers(self):
        if self.mode not in [
                Mode.EXACT, Mode.IN, Mode.CONTAINS, Mode.INSENSITIVE_CONTAINS, Mode.INSENSITIVE_EXACT,
                Mode.STARTS_WITH, Mode.ENDS_WITH
        ]:

            raise ValidationException(f'Mode {self.mode} is not supported for string field {self.field}')

        self.set_lookup()
        return self.value, None
