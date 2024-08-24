import pytest
from rest_framework.test import APIRequestFactory

from breathecode.admissions.models import Academy, Cohort
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode
from capyc.django.serializer import Serializer


class AcademySerializer(Serializer):
    model = Academy
    fields = {
        "default": ("id", "name", "slug"),
        "contact": ("street_address", "feedback_email"),
        "saas": ("available_as_saas", "is_hidden_on_prework"),
    }
    filters = ("slug", "name")
    depth = 2


class CohortSerializer(Serializer):
    model = Cohort
    fields = {
        "default": ("id", "name", "slug"),
        "intro": ("intro_video", "available_as_saas"),
        "ids": ("academy", "syllabus_version"),
    }
    filters = ("slug", "name", "academy__*")
    depth = 2

    academy = AcademySerializer


@pytest.fixture(autouse=True)
def setup(db):
    yield


@pytest.mark.django_db(reset_sequences=True)
def test_default(bc: Breathecode):
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


@pytest.mark.asyncio
@pytest.mark.django_db(reset_sequences=True)
async def test_some_sets(bc: Breathecode):
    model = await bc.database.acreate(cohort=2)

    factory = APIRequestFactory()
    request = factory.get("/notes/547/?sets=intro,not-found")

    qs = Cohort.objects.all()
    serializer = CohortSerializer(data=qs, many=True, request=request)

    assert await serializer.adata == [
        {
            "id": x.id,
            "slug": x.slug,
            "name": x.name,
            "intro_video": x.intro_video,
            "available_as_saas": x.available_as_saas,
        }
        for x in model.cohort
    ]


@pytest.mark.asyncio
@pytest.mark.django_db(reset_sequences=True)
async def test_one_set(bc: Breathecode):
    model = await bc.database.acreate(cohort=2)

    factory = APIRequestFactory()
    request = factory.get("/notes/547/?sets=intro,not-found")

    qs = Cohort.objects.all()
    serializer = CohortSerializer(data=qs, many=True, request=request)

    assert await serializer.adata == [
        {
            "id": x.id,
            "slug": x.slug,
            "name": x.name,
            "intro_video": x.intro_video,
            "available_as_saas": x.available_as_saas,
        }
        for x in model.cohort
    ]


@pytest.mark.asyncio
@pytest.mark.django_db(reset_sequences=True)
async def test_two_sets(bc: Breathecode):
    model = await bc.database.acreate(cohort=2)

    factory = APIRequestFactory()
    request = factory.get("/notes/547/?sets=intro,ids")

    qs = Cohort.objects.all()
    serializer = CohortSerializer(data=qs, many=True, request=request)

    assert await serializer.adata == [
        {
            "id": x.id,
            "slug": x.slug,
            "name": x.name,
            "intro_video": x.intro_video,
            "available_as_saas": x.available_as_saas,
            "academy": x.academy.id,
            "syllabus_version": None,
        }
        for x in model.cohort
    ]


@pytest.mark.asyncio
@pytest.mark.django_db(reset_sequences=True)
async def test_two_sets_expanded(bc: Breathecode):
    model = await bc.database.acreate(cohort=2)

    factory = APIRequestFactory()
    request = factory.get("/notes/547/?sets=intro,ids&expand=academy,syllabus_version")

    qs = Cohort.objects.all()
    serializer = CohortSerializer(data=qs, many=True, request=request)

    assert await serializer.adata == [
        {
            "id": x.id,
            "slug": x.slug,
            "name": x.name,
            "intro_video": x.intro_video,
            "available_as_saas": x.available_as_saas,
            "academy": {
                "id": x.academy.id,
                "name": x.academy.name,
                "slug": x.academy.slug,
            },
            "syllabus_version": None,
        }
        for x in model.cohort
    ]


@pytest.mark.asyncio
@pytest.mark.django_db(reset_sequences=True)
async def test_two_sets_expanded___(bc: Breathecode):
    model = await bc.database.acreate(cohort=2)

    factory = APIRequestFactory()
    request = factory.get("/notes/547/?sets=intro,ids&expand=academy[contact,saas],syllabus_version")

    qs = Cohort.objects.all()
    serializer = CohortSerializer(data=qs, many=True, request=request)

    assert await serializer.adata == [
        {
            "id": x.id,
            "slug": x.slug,
            "name": x.name,
            "intro_video": x.intro_video,
            "available_as_saas": x.available_as_saas,
            "academy": {
                "id": x.academy.id,
                "name": x.academy.name,
                "slug": x.academy.slug,
                "street_address": x.academy.street_address,
                "feedback_email": x.academy.feedback_email,
                "available_as_saas": x.academy.available_as_saas,
                "is_hidden_on_prework": x.academy.is_hidden_on_prework,
            },
            "syllabus_version": None,
        }
        for x in model.cohort
    ]
