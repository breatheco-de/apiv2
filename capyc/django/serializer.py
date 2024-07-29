class InitializeMeta(type):

    def __init__(cls, name, bases, dct):
        super().__init__(name, bases, dct)
        cls.initialize()


class Serializer: ...


from breathecode.admissions.models import Cohort


class CohortSerializer(Serializer):
    model = Cohort
    fields = ()
    # exclude = ()
