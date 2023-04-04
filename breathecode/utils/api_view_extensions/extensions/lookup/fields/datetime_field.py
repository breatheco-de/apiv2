from datetime import timedelta
import random
from breathecode.utils.api_view_extensions.extensions.lookup.fields.generic.lookup_field import LookupField
from breathecode.utils.i18n import translation
from django.db.models import Q

from breathecode.utils.validation_exception import ValidationException
from django.utils import timezone
from ..mode import Mode

__all__ = ['LookupExtension']


class DatetimeField(LookupField):

    def generator(self) -> str:
        delta = random.randint(0, 10000000)
        sign = bool(random.randbytes(1))
        date = timezone.now()

        if sign:
            date += timedelta(seconds=delta)

        else:
            date -= timedelta(seconds=delta)

        return date.isoformat()

    def validator(self, lang, value):
        from django.utils import dateparse

        if self.mode == Mode.IS_NULL:
            return value == 'true'

        if self.mode in [Mode.YEAR, Mode.MONTH, Mode.DAY, Mode.HOUR, Mode.MINUTE]:
            try:
                return int(value)

            except ValidationException:
                raise ValidationException(
                    translation(lang,
                                en=f'{self.field} must be an integer',
                                es=f'{self.field} debe ser un entero',
                                slug=f'{self.field.replace("_", "-")}-must-be-an-integer'))

        if self.mode in [
                Mode.EXACT, Mode.GREATER_THAN, Mode.GREATER_THAN_EQUAL, Mode.LOWER_THAN, Mode.LOWER_THAN_EQUAL
        ]:

            if not (result := dateparse.parse_datetime(value)):
                raise ValidationException(
                    translation(lang,
                                en=f'{self.field} must be a datetime',
                                es=f'{self.field} debe ser un datetime',
                                slug=f'{self.field.replace("_", "-")}-must-be-a-datetime'))

            return result

        raise ValidationException(f'Mode {self.mode} is not supported for datetime field {self.field}')

    def value(self, value):
        return Q(**{f'{self.prefix}{self.field}{self.suffix}': value})

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
                Mode.EXACT, Mode.YEAR, Mode.MONTH, Mode.DAY, Mode.HOUR, Mode.MINUTE, Mode.GREATER_THAN,
                Mode.GREATER_THAN_EQUAL, Mode.LOWER_THAN, Mode.LOWER_THAN_EQUAL, Mode.IS_NULL
        ]:

            raise ValidationException(f'Mode {self.mode} is not supported for datetime field {self.field}')

        self.lookup = f'{self.prefix}{self.field}'

        if self.mode == Mode.EXACT:
            self.suffix = ''

        if self.mode == Mode.YEAR:
            self.suffix = '__year'

        if self.mode == Mode.MONTH:
            self.suffix = '__month'

        if self.mode == Mode.DAY:
            self.suffix = '__day'

        if self.mode == Mode.HOUR:
            self.suffix = '__hour'

        if self.mode == Mode.MINUTE:
            self.suffix = '__minute'

        if self.mode == Mode.GREATER_THAN:
            self.suffix = '__gt'

        if self.mode == Mode.GREATER_THAN_EQUAL:
            self.suffix = '__gte'

        if self.mode == Mode.LOWER_THAN:
            self.suffix = '__lt'

        if self.mode == Mode.LOWER_THAN_EQUAL:
            self.suffix = '__lte'

        if self.mode == Mode.IS_NULL:
            self.suffix = '__isnull'

    def handlers(self):
        self.set_lookup()
        return self.value, self.validator, self.generator
