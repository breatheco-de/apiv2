from breathecode.mentorship.models import MentorshipService
from breathecode.services import LaunchDarkly


def mentorship_service(client: LaunchDarkly, mentorship_service: MentorshipService):
    key = f"{mentorship_service.id}"
    name = f"{mentorship_service.name} ({mentorship_service.slug})"
    kind = "mentoring-service"
    context = {
        "id": mentorship_service.id,
        "slug": mentorship_service.slug,
        "max_duration": mentorship_service.max_duration,
        "language": mentorship_service.language,
        "academy": mentorship_service.academy.slug,
    }

    return client.context(key, name, kind, context)
