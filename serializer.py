import os

import django

# Set the Django settings module.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "breathecode.settings")

# Configure Django.
django.setup()


class SerializerMeta(type):

    def __init__(cls, name, bases, dct):
        super().__init__(name, bases, dct)
        ...


class Serializer(metaclass=SerializerMeta): ...


from breathecode.admissions.models import Cohort


class CohortSerializer(Serializer):
    model = Cohort
    fields = ()
    # exclude = ()
