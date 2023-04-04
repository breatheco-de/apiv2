from faker import Faker

from django.db.models import Q

from ...mode import Mode

__all__ = ['LookupExtension']


class LookupField:
    fake: Faker
    prefix: str

    def validator(self, lang, value):
        raise NotImplementedError()

    def value(self, value):
        return Q(**{f'{self.prefix}{self.field}{self.suffix}': value})

    def append_prefix(self, prefix):
        self.prefix = prefix + self.prefix

    def __init__(self, model, field, mode: Mode):
        self.fake = Faker()

    def set_lookup(self):
        raise NotImplementedError()

    def handlers(self):
        raise NotImplementedError()
