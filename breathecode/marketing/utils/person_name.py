import re
import unicodedata
from typing import Optional

_MULTI_SPACE = re.compile(r"\s+")


def standardize_person_name(value: Optional[str]) -> str:
    """
    Normalize person names for storage and CRM: Unicode NFKC (e.g. mathematical script 𝓜𝓪𝓻𝓲𝓪 → Maria),
    collapse whitespace, casefold to lowercase.
    """
    if value is None:
        return ""
    if not isinstance(value, str):
        value = str(value)
    value = unicodedata.normalize("NFKC", value)
    value = _MULTI_SPACE.sub(" ", value).strip()
    return value.casefold()
