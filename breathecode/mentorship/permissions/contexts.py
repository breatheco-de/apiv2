from breathecode.mentorship.models import MentorshipService
from breathecode.services import LaunchDarkly


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
