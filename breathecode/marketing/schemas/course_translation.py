from __future__ import annotations

import copy
from typing import Any, Dict

from django.forms import ValidationError
from jsonschema import Draft7Validator, ValidationError as JSONSchemaValidationError

__all__ = [
    "COURSE_TRANSLATION_SCHEMAS",
    "export_course_translation_schemas",
    "validate_course_translation_field",
]


def _non_empty_string() -> Dict[str, Any]:
    return {"type": "string", "minLength": 1}


COURSE_TRANSLATION_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "course_modules": {
        "type": ["array", "null"],
        "items": {
            "type": "object",
            "required": ["slug", "name", "description"],
            "properties": {
                "slug": _non_empty_string(),
                "name": _non_empty_string(),
                "description": _non_empty_string(),
                "icon_url": {"type": ["string", "null"], "format": "uri-reference"},
                "duration": {"type": ["string", "null"]},
                "topics": {
                    "type": ["array", "null"],
                    "items": _non_empty_string(),
                },
                "resources": {
                    "type": ["array", "null"],
                    "items": {
                        "type": "object",
                        "required": ["title", "url"],
                        "properties": {
                            "title": _non_empty_string(),
                            "url": {"type": "string", "format": "uri"},
                        },
                        "additionalProperties": False,
                    },
                },
            },
            "additionalProperties": False,
        },
    },
    "landing_variables": {
        "type": ["object", "null"],
        "properties": {
            "build-connector": {
                "type": ["object", "null"],
                "properties": {
                    "build": {"type": ["string", "null"]},
                    "description": {"type": ["string", "null"]},
                    "link": {"type": ["string", "null"]},
                    "what-you-will": {"type": ["string", "null"]},
                },
                "additionalProperties": False,
            },
            "certificate": {
                "type": ["object", "null"],
                "properties": {
                    "button": {"type": ["string", "null"]},
                    "button-link": {"type": ["string", "null"]},
                    "description": {"type": ["string", "null"]},
                    "image": {"type": ["string", "null"]},
                    "title": {"type": ["string", "null"]},
                },
                "additionalProperties": False,
            },
            "contact_methods": {
                "type": ["object", "null"],
                "properties": {
                    "whatsapp": {
                        "type": ["object", "null"],
                        "properties": {
                            "contact_image": {"type": ["string", "null"]},
                            "number": {"type": ["string", "null"]},
                            "subtitle": {"type": ["string", "null"]},
                            "title": {"type": ["string", "null"]},
                        },
                        "additionalProperties": False,
                    }
                },
                "additionalProperties": False,
            },
            "faq": {
                "type": ["array", "null"],
                "items": {
                    "type": "object",
                    "required": ["title", "description"],
                    "properties": {
                        "id": {"type": ["integer", "string", "null"]},
                        "title": _non_empty_string(),
                        "description": _non_empty_string(),
                    },
                    "additionalProperties": False,
                },
            },
            "featured-bullets": {
                "type": ["array", "null"],
                "items": {
                    "type": "object",
                    "required": ["title"],
                    "properties": {
                        "title": _non_empty_string(),
                    },
                    "additionalProperties": False,
                },
            },
            "features": {
                "type": ["object", "null"],
                "properties": {
                    "list": {
                        "type": ["array", "null"],
                        "items": {
                            "type": "object",
                            "required": ["title"],
                            "properties": {
                                "icon": {"type": ["string", "null"]},
                                "id": {"type": ["integer", "string", "null"]},
                                "title": _non_empty_string(),
                            },
                            "additionalProperties": False,
                        },
                    },
                    "showOnSignup": {
                        "type": ["array", "null"],
                        "items": {
                            "type": "object",
                            "required": ["title"],
                            "properties": {
                                "icon": {"type": ["string", "null"]},
                                "title": _non_empty_string(),
                                "type": {"type": ["string", "null"]},
                            },
                            "additionalProperties": False,
                        },
                    },
                    "what-is-learnpack": {
                        "type": ["object", "null"],
                        "properties": {
                            "description": {"type": ["string", "null"]},
                            "title": {"type": ["string", "null"]},
                        },
                        "additionalProperties": False,
                    },
                },
                "additionalProperties": False,
            },
            "job-section": {
                "type": ["object", "null"],
                "properties": {
                    "button-link": {"type": ["string", "null"]},
                    "description": {"type": ["string", "null"]},
                    "subtitle": {"type": ["string", "null"]},
                    "title": {"type": ["string", "null"]},
                },
                "additionalProperties": False,
            },
            "show-free-course": {"type": ["string", "boolean", "null"]},
            "show-pricing-section": {"type": ["string", "boolean", "null"]},
            "sign-up-to-plus": {"type": ["string", "null"]},
            "sign-up-to-plus-description": {"type": ["string", "null"]},
            "why-learn-4geeks-connector": {
                "type": ["object", "null"],
                "properties": {
                    "benefits-connector": {"type": ["string", "null"]},
                    "who": {"type": ["string", "null"]},
                    "why-learn-with": {"type": ["string", "null"]},
                },
                "additionalProperties": False,
            },
            "card": {
                "type": ["array", "null"],
                "items": {
                    "type": "object",
                    "required": ["title"],
                    "properties": {
                        "icon": {"type": ["string", "null"]},
                        "title": _non_empty_string(),
                        "value": {"type": ["string", "null"]},
                    },
                    "additionalProperties": False,
                },
            },
            "course-content-description": {"type": ["string", "null"]},
            "course-content-text": {"type": ["string", "null"]},
        },
        "additionalProperties": True,
    },
    "prerequisite": {
        "type": ["array", "null"],
        "items": _non_empty_string(),
    },
}


def _build_validators() -> Dict[str, Draft7Validator]:
    validators: Dict[str, Draft7Validator] = {}
    for field, schema in COURSE_TRANSLATION_SCHEMAS.items():
        validators[field] = Draft7Validator(schema)
    return validators


_VALIDATORS = _build_validators()


def _format_error(error: JSONSchemaValidationError) -> str:
    path = ".".join(str(p) for p in error.path)
    if path:
        return f"{path}: {error.message}"
    return error.message


def validate_course_translation_field(field: str, value: Any) -> None:
    validator = _VALIDATORS[field]
    errors = sorted(validator.iter_errors(value), key=lambda e: e.path)
    if errors:
        formatted = [_format_error(error) for error in errors]
        raise ValidationError(formatted)


def export_course_translation_schemas() -> Dict[str, Any]:
    # Return deep copies so downstream code cannot mutate the base schemas.
    return {key: copy.deepcopy(value) for key, value in COURSE_TRANSLATION_SCHEMAS.items()}

