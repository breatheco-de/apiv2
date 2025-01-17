from typing import Optional

from capyc.core.managers import feature
from django.db.models.query_utils import Q

from breathecode.admissions.models import Academy, Cohort
from breathecode.assignments.models import Task
from breathecode.authenticate.models import User
from breathecode.events.models import Event, LiveClass
from breathecode.mentorship.models import MentorshipService
from breathecode.payments.models import CohortSet, MentorshipServiceSet
from breathecode.registry.models import Asset
from breathecode.utils.decorators.consume import ServiceContext

flags = feature._flags


@feature.availability("payments.bypass_consumption")
def bypass_consumption(context: ServiceContext, kwargs: Optional[dict] = None, user: Optional[User] = None) -> bool:
    """
    This flag is used to bypass the consumption of a service.

    Arguments:
        context: ServiceContext - The context of the service.
        args: Optional[tuple] - The arguments of the service.
        kwargs: Optional[dict] - The keyword arguments of the service.
        user: Optional[User] - The user to bypass the consumption for, if none it will use request.user.
    """
    from breathecode.payments.data import get_virtual_consumables

    if kwargs is None:
        kwargs = {}

    if flags.get("BYPASS_CONSUMPTION") in feature.TRUE:
        return True

    virtual_consumables = get_virtual_consumables()
    user = user or context["request"].user

    event_id = kwargs.get("event_id")
    event_slug = kwargs.get("event_slug")
    if context["service"] == "event_join" and (event_id or event_slug):

        pk = Q(id=event_id) | Q(slug=event_slug, slug__isnull=False)
        event_type_set_ids = [
            consumable["event_type_set"]["id"] for consumable in virtual_consumables if consumable["event_type_set"]
        ]

        event = Event.objects.filter(pk, event_type__eventtypeset__in=event_type_set_ids).first()
        if not event:
            return False

        if event.academy and event.academy.available_as_saas:
            return False

        return True

    hash = kwargs.get("hash")
    if context["service"] == "live_class_join" and (hash := kwargs.get("hash")):
        live_class = LiveClass.objects.filter(hash=hash).first()
        if live_class is None:
            return False

        cohort = live_class.cohort_time_slot.cohort
        if cohort.available_as_saas is True or (
            cohort.available_as_saas is None and cohort.academy.available_as_saas is True
        ):
            return False

        cohort_set_ids = [consumable["cohort_set"]["id"] for consumable in virtual_consumables]
        if CohortSet.objects.filter(cohorts=cohort, id__in=cohort_set_ids).exists():
            return True

        return False

    if context["service"] == "join_mentorship" and (service_slug := kwargs.get("service_slug")):

        mentorship_service_set_ids = [
            consumable["mentorship_service_set"]["id"]
            for consumable in virtual_consumables
            if consumable["mentorship_service_set"]
        ]

        if MentorshipServiceSet.objects.filter(
            mentorship_services__slug=service_slug,
            mentorship_services__academy__available_as_saas=False,
            id__in=mentorship_service_set_ids,
        ).exists():
            return True

        return False

    if context["service"] == "add_code_review" and (task_id := kwargs.get("task_id")):
        cohort_set_ids = [
            consumable["cohort_set"]["id"] for consumable in virtual_consumables if consumable["cohort_set"]
        ]

        task = Task.objects.filter(id=task_id, cohort__cohortset__id__in=cohort_set_ids).first()
        if task is None:
            return False

        if task.cohort.available_as_saas is True or (
            task.cohort.available_as_saas is None and task.cohort.academy.available_as_saas is True
        ):
            return False

        return True

    if context["service"] == "read_lesson" and (asset_slug := kwargs.get("asset_slug")):
        cohort_set_ids = [
            consumable["cohort_set"]["id"] for consumable in virtual_consumables if consumable["cohort_set"]
        ]
        request = context["request"]
        asset = Asset.get_by_slug(asset_slug, request)
        if asset is None:
            return False

        if Cohort.objects.filter(
            Q(available_as_saas=False) | Q(available_as_saas=None, academy__available_as_saas=False),
            cohortuser__user=user,
            syllabus_version__json__icontains=f'"{asset_slug}"',
            cohortset__id__in=cohort_set_ids,
        ).exists():
            return True

        return False

    return False


blocked_user_ids = {
    "mentorship-service": {
        # Blocked users in the entire platform (Add user ids)
        "from_everywhere": [1],
        # Blocked users in the academy, add user id and academy slug
        "from_academy": [(1, "downtown-miami")],
        # Blocked users in a cohort, add user id and cohort slug
        "from_cohort": [(1, "4geeks-fs-1")],
        # Blocked users of a service, add user id and mentorship service slug
        "from_mentorship_service": [(1, "geekpal-1-1")],
    }
}


@feature.availability("payments.can_access")
def can_access(
    to: str,
    user: User,
    cohort: Optional[Cohort] = None,
    academy: Optional[Academy] = None,
    mentorship_service: Optional[MentorshipService] = None,
) -> bool:

    if to not in blocked_user_ids:
        return True

    x = blocked_user_ids[to]

    if user.id in x["from_everywhere"]:
        return False

    if academy and (academy, academy.slug) in x["from_academy"]:
        return False

    if cohort and (user.id, cohort.slug) in x["from_cohort"]:
        return False

    if mentorship_service and (user.id, mentorship_service.slug) in x["from_mentorship_service"]:
        return False

    return True


feature.add(bypass_consumption, can_access)
