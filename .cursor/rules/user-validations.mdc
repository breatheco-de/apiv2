---
description:
globs: breathecode/*/views.py,breathecode/*/actions.py
alwaysApply: false
---



When building a APIView and rising a ValidationException make sure to include the error messages using translations like this:

```python
from capyc.core.i18n import translation
from capyc.rest_framework.exceptions import ValidationException

raise ValidationException(
    translation(
        en=f"Cannot remove user={user.id} from organization because they are whitelisted",
        es=f"No se pudo remover usuario id={user.id} de la organization porque está en la lista blanca",
    ),
    slug="user-whitelisted",
)
```
