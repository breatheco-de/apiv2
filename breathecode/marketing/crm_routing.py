import datetime
import logging
from decimal import Decimal
from functools import lru_cache
from uuid import UUID

from cel_expr_python import cel
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

_CEL_ENV = cel.NewEnv(variables={"lead": cel.Type.DYN})


@lru_cache(maxsize=256)
def _compile_condition(condition):
    return _CEL_ENV.compile(condition)


def validate_crm_condition(condition):
    """Compile a CRM routing condition before it is persisted."""
    if not condition:
        return

    try:
        expression = _compile_condition(condition)
        if expression.return_type() != cel.Type.BOOL:
            raise ValueError("CRM routing CEL expressions must return a boolean")
    except Exception as exc:
        raise ValidationError({"condition": f"Invalid CEL expression: {exc}"}) from exc


def _to_cel_value(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime.datetime, datetime.date, datetime.time)):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _to_cel_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_cel_value(item) for item in value]
    return str(value)


def build_form_entry_context(form_entry):
    """Expose persisted FormEntry fields as a CEL-compatible map."""
    lead = {}
    for field in form_entry._meta.concrete_fields:
        lead[field.name] = _to_cel_value(field.value_from_object(form_entry))

    lead["custom"] = _to_cel_value(form_entry.custom_fields or {})
    return {"lead": lead}


def matches_crm_condition(form_entry, condition):
    """Return whether one persisted FormEntry matches a CEL condition."""
    if not condition:
        return True

    try:
        result = _compile_condition(condition).eval(data=build_form_entry_context(form_entry))
        value = result.value()
        if not isinstance(value, bool):
            raise ValueError("CRM routing CEL expressions must return a boolean")
        return value
    except Exception:
        logger.exception("Unable to evaluate CRM routing condition %r", condition)
        return False
