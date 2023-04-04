from typing import Any
from breathecode.utils.api_view_extensions.extensions.lookup.fields.datetime_field import DatetimeField
from breathecode.utils.api_view_extensions.extensions.lookup.fields.id_field import IDField
from breathecode.utils.api_view_extensions.extensions.lookup.fields.integer_field import IntegerField
from breathecode.utils.api_view_extensions.extensions.lookup.fields.string_field import StringField
from django.db import models

from breathecode.utils.api_view_extensions.extensions.lookup.mode import Mode
from breathecode.utils.validation_exception import ValidationException


def get_field(field: Any, mode: Mode, handler: Any):
    field_class = handler.field.__class__

    if field_class == models.URLField:
        return StringField(handler.field.related_model, field, mode)

    if field_class == models.IntegerField:
        return IntegerField(handler.field.related_model, field, mode)

    if field_class == models.CharField:
        return StringField(handler.field.related_model, field, mode)

    if field_class == models.TextField:
        return StringField(handler.field.related_model, field, mode)

    if field_class == models.BooleanField:
        return bool_field(field, mode)

    if field_class == models.DateField:
        return date_field(field, mode)

    if field_class == models.DateTimeField:
        return DatetimeField(handler.field.related_model, field, mode)

    if field_class == models.BigIntegerField:
        return DatetimeField(handler.field.related_model, field, mode)

    if field_class == models.ForeignKey:
        return IDField(handler.field.related_model, field, mode)

    if field_class == models.ManyToManyField:
        return many_to_many_field(field, mode)

    if field_class == models.OneToOneField:
        return IDField(field, mode)

    if field_class == models.JSONField:
        return json_field(field, mode)

    if field_class == models.DecimalField:
        return decimal_field(field, mode)

    if field_class == models.FloatField:
        return float_field(field, mode)

    if field_class == models.EmailField:
        return StringField(handler.field.related_model, field, mode)

    raise ValidationException(f'Field {field} is not a django field ({field_class})')
