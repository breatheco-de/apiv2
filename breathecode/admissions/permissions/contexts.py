from breathecode.admissions.models import Academy
from breathecode.services import LaunchDarkly


def academy(client: LaunchDarkly, academy: Academy):
    key = f"{academy.id}"
    name = f"{academy.name} ({academy.slug})"
    kind = "academy"
    context = {
        "id": academy.id,
        "slug": academy.slug,
        "city": academy.city.name,
        "country": academy.country.name,
        "zip_code": academy.zip_code,
        "timezone": academy.timezone,
    }

    return client.context(key, name, kind, context)
