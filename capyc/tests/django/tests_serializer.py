import pytest

from breathecode.admissions.models import Academy, Cohort
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode
from capyc.django.serializer import Serializer


class AcademySerializer(Serializer):
    model = Academy
    filters = ("slug", "name")
    fields = ("id", "slug", "name")
    depth = 2


class CohortSerializer(Serializer):
    model = Cohort
    filters = ("slug", "name", "academy__*")
    fields = ("id", "slug", "name")
    depth = 2

    academy = AcademySerializer


@pytest.fixture(autouse=True)
def setup(db):
    yield


def test_xyz(bc: Breathecode):
    model = bc.database.create(cohort=2)

    qs = Cohort.objects.all()
    serializer = CohortSerializer(data=qs, many=True)

    assert serializer.data == [
        {
            "id": x.id,
            "slug": x.slug,
            "name": x.name,
        }
        for x in model.cohort
    ]
