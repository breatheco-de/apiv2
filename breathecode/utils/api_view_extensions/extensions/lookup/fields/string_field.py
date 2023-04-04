from django.db.models import Q
from breathecode.utils.api_view_extensions.extensions.lookup.fields.generic.lookup_field import LookupField

from breathecode.utils.validation_exception import ValidationException
from ..mode import Mode

__all__ = ['LookupExtension']


class StringField(LookupField):

    def generator(self) -> str:
        return self.fake.slug()

    def value(self, value):
        return Q(**{self.prefix + self.lookup + self.suffix: value})

    def append_prefix(self, prefix):
        self.prefix = prefix + self.prefix

    def __init__(self, model, field, mode: Mode):
        super().__init__(model, field, mode)
        self.model = model
        self.prefix = ''
        self.suffix = ''
        self.field = field
        self.mode = mode

    def set_lookup(self):
        if self.mode not in [
                Mode.EXACT, Mode.IN, Mode.CONTAINS, Mode.INSENSITIVE_CONTAINS, Mode.INSENSITIVE_EXACT,
                Mode.STARTS_WITH, Mode.ENDS_WITH
        ]:

            raise ValidationException(f'Mode {self.mode} is not supported for string field {self.field}')

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
        self.set_lookup()
        return self.value, None, self.generator
