import json
import re
from datetime import datetime

from django.utils import timezone
from rest_framework.exceptions import ValidationError

from breathecode.utils.validation_exception import ValidationException

ACTIVITY_FIELDS = [
    'cohort',
    'data',
    'day',
    'slug',
    'user_agent',
]

ACTIVITY_REQUIRED_FIELDS = [
    'slug',
    'user_agent',
]

ACTIVITY_TYPE_DONT_NEED_A_COHORT = [
    'breathecode-login',
    'online-platform-registration',
]

ACTIVITY_TYPE_DONT_NEED_A_DATA = [
    'breathecode-login',
    'online-platform-registration',
]


def validate_activity_fields(data):
    for field in data:
        if field not in ACTIVITY_FIELDS:
            slug = field.replace('_', '-')
            raise ValidationException(
                f'Field {field} is not allowed in the request',
                slug=f'{slug}-not-allowed')


def validate_require_activity_fields(data):
    for field in ACTIVITY_REQUIRED_FIELDS:
        if field not in data:
            slug = field.replace('_', '-')
            raise ValidationException(f'Missing {field} in the request',
                                      slug=f'missing-{slug}')


def validate_if_activity_need_field_cohort(data):
    slug = data.get('slug')
    if 'cohort' not in data and slug not in ACTIVITY_TYPE_DONT_NEED_A_COHORT:
        raise ValidationException(
            'This activity type need a cohort in the request',
            slug='missing-cohort')


def validate_if_activity_need_field_data(data):
    slug = data.get('slug')
    if 'data' not in data and slug not in ACTIVITY_TYPE_DONT_NEED_A_DATA:
        raise ValidationException(
            'This activity type need a data field in the request',
            slug='missing-data')


def validate_activity_have_correct_data_field(data):
    if 'data' in data:
        try:
            json.loads(data['data'])

        except Exception as e:
            raise ValidationException('Data is not a JSON',
                                      slug='data-is-not-a-json')


def generate_created_at():
    return timezone.make_aware(datetime.now())
