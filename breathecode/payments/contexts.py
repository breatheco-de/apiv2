from breathecode.admissions.models import Academy
from breathecode.authenticate.models import User
from breathecode.mentorship.models import MentorshipService
from breathecode.services import LaunchDarkly


def user(client: LaunchDarkly, user: User):
    key = f'user-{user.id}'
    name = f'{user.first_name} {user.last_name} ({user.email})'
    kind = 'user-data'
    context = {
        'id': user.id,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'username': user.username,
        'is_staff': user.is_staff,
        'is_active': user.is_active,
        'date_joined': user.date_joined,
        'groups': [x.name for x in user.groups.all()],
    }

    return client.context(key, name, kind, context)


def mentorship_service(client: LaunchDarkly, mentorship_service: MentorshipService):
    key = f'mentorship-service-{mentorship_service.id}'
    name = f'{mentorship_service.name} ({mentorship_service.slug})'
    kind = 'mentoring-services'
    context = {
        'id': mentorship_service.id,
        'name': mentorship_service.name,
        'slug': mentorship_service.slug,
        'duration': mentorship_service.duration,
        'max_duration': mentorship_service.max_duration,
        'language': mentorship_service.language,
        'allow_mentee_to_extend': mentorship_service.allow_mentee_to_extend,
        'allow_mentors_to_extend': mentorship_service.allow_mentors_to_extend,
        'academy': mentorship_service.academy.slug,
    }

    return client.context(key, name, kind, context)


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
