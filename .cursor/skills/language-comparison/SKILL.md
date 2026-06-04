---
name: language-comparison
description: Use when comparing two language codes or querying/filtering by language in the API. Ensures "us" and "en" are treated as the same language via shared helpers from breathecode.utils.validators.
---

# Language comparison (us / en)

When comparing language codes or querying/filtering by language in this codebase, always use the shared helpers so that `"us"` and `"en"` are treated as the same language.

## Comparing two language values

Use `languages_equivalent(lang_a, lang_b)` instead of raw `==`, `!=`, or `.lower()` comparisons.

```python
from breathecode.utils.validators import languages_equivalent

# Do not: if lang != category.lang:
# Do not: if lang.lower() != category.lang.lower():
if not languages_equivalent(lang, category.lang):
    ...
```

## Querying / filtering by language

Use `language_codes_for_lookup(lang)` and filter with `lang__in=codes` so both `"us"` and `"en"` match English. Do not use `filter(lang=lang)` when the field may store either code for English.

```python
from breathecode.utils.validators import language_codes_for_lookup

codes = language_codes_for_lookup(lang)
translated = model.all_translations.filter(lang__in=codes).first() if codes else None
```

## Import

```python
from breathecode.utils.validators import languages_equivalent, language_codes_for_lookup
```
