from breathecode.admissions.models import Academy
from breathecode.services import LaunchDarkly


def academy(client: LaunchDarkly, academy: Academy):
    key = f'academy-{academy.id}'
    name = f'{academy.name} ({academy.slug})'
    kind = 'mentoring-services'
    context = {
        'id': academy.id,
        'slug': academy.slug,
        'name': academy.name,
        'city': academy.city.name,
        'country': academy.country.name,
        'zip_code': academy.zip_code,
        'available_as_saas': academy.available_as_saas,
        'is_hidden_on_prework': academy.is_hidden_on_prework,
        'status': academy.status,
        'timezone': academy.timezone,
    }

    return client.context(key, name, kind, context)
