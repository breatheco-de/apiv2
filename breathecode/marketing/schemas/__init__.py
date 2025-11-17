"""
Utilities and schema definitions for marketing course translation payloads.
"""

from .course_translation import (
    COURSE_TRANSLATION_SCHEMAS,
    export_course_translation_schemas,
    validate_course_translation_field,
)

__all__ = [
    "COURSE_TRANSLATION_SCHEMAS",
    "export_course_translation_schemas",
    "validate_course_translation_field",
]

