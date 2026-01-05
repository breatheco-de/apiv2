import capyc.pytest as capy
import pytest
from capyc.rest_framework.exceptions import ValidationException
from django.core.exceptions import ValidationError as DjangoValidationError

from breathecode.feedback.models import SurveyConfiguration, SurveyStudy
from breathecode.feedback.serializers import SurveyStudySerializer


def _create_survey_configuration(*, academy, created_by, trigger_type):
    return SurveyConfiguration.objects.create(
        trigger_type=trigger_type,
        syllabus={},
        template=None,
        questions={"questions": [{"id": "q1", "type": "score", "title": "How was it?"}]},
        is_active=True,
        academy=academy,
        created_by=created_by,
    )


def test_survey_study_serializer_rejects_mixed_trigger_types(database: capy.Database, fake: capy.Fake):
    model = database.create(user=1, academy=1)

    c1 = _create_survey_configuration(
        academy=model.academy,
        created_by=model.user,
        trigger_type=SurveyConfiguration.TriggerType.MODULE_COMPLETION,
    )
    c2 = _create_survey_configuration(
        academy=model.academy,
        created_by=model.user,
        trigger_type=SurveyConfiguration.TriggerType.COURSE_COMPLETION,
    )

    serializer = SurveyStudySerializer(
        data={
            "slug": fake.slug(),
            "title": fake.name(),
            "survey_configurations": [c1.id, c2.id],
        }
    )

    with pytest.raises(ValidationException):
        serializer.is_valid(raise_exception=True)


def test_survey_study_serializer_allows_single_trigger_type(database: capy.Database, fake: capy.Fake):
    model = database.create(user=1, academy=1)

    c1 = _create_survey_configuration(
        academy=model.academy,
        created_by=model.user,
        trigger_type=SurveyConfiguration.TriggerType.MODULE_COMPLETION,
    )
    c2 = _create_survey_configuration(
        academy=model.academy,
        created_by=model.user,
        trigger_type=SurveyConfiguration.TriggerType.MODULE_COMPLETION,
    )

    serializer = SurveyStudySerializer(
        data={
            "slug": fake.slug(),
            "title": fake.name(),
            "survey_configurations": [c1.id, c2.id],
        }
    )

    assert serializer.is_valid(raise_exception=True) is True


def test_survey_study_serializer_allows_all_null_trigger_type(database: capy.Database, fake: capy.Fake):
    model = database.create(user=1, academy=1)

    c1 = _create_survey_configuration(academy=model.academy, created_by=model.user, trigger_type=None)
    c2 = _create_survey_configuration(academy=model.academy, created_by=model.user, trigger_type=None)

    serializer = SurveyStudySerializer(
        data={
            "slug": fake.slug(),
            "title": fake.name(),
            "survey_configurations": [c1.id, c2.id],
        }
    )

    assert serializer.is_valid(raise_exception=True) is True


def test_survey_study_serializer_rejects_mixed_trigger_types_on_update(database: capy.Database, fake: capy.Fake):
    model = database.create(user=1, academy=1)

    study = SurveyStudy.objects.create(slug=fake.slug(), title=fake.name(), academy=model.academy)

    c1 = _create_survey_configuration(
        academy=model.academy,
        created_by=model.user,
        trigger_type=SurveyConfiguration.TriggerType.MODULE_COMPLETION,
    )
    c2 = _create_survey_configuration(
        academy=model.academy,
        created_by=model.user,
        trigger_type=SurveyConfiguration.TriggerType.COURSE_COMPLETION,
    )

    serializer = SurveyStudySerializer(
        study,
        data={
            "survey_configurations": [c1.id, c2.id],
        },
        partial=True,
    )

    with pytest.raises(ValidationException):
        serializer.is_valid(raise_exception=True)


def test_survey_study_m2m_changed_signal_blocks_mixed_trigger_types(database: capy.Database, fake: capy.Fake):
    model = database.create(user=1, academy=1)

    study = SurveyStudy.objects.create(slug=fake.slug(), title=fake.name(), academy=model.academy)

    c1 = _create_survey_configuration(
        academy=model.academy,
        created_by=model.user,
        trigger_type=SurveyConfiguration.TriggerType.MODULE_COMPLETION,
    )
    c2 = _create_survey_configuration(
        academy=model.academy,
        created_by=model.user,
        trigger_type=SurveyConfiguration.TriggerType.COURSE_COMPLETION,
    )

    study.survey_configurations.add(c1)

    with pytest.raises(DjangoValidationError):
        study.survey_configurations.add(c2)


