import logging
from django.contrib.auth.models import AnonymousUser

logger = logging.getLogger(__name__)

__all__ = ["localize_query"]


def localize_query(query, request, matcher=None):
    from breathecode.authenticate.models import ProfileAcademy

    # not a part of the staff, cannot access all info
    if isinstance(request.user, AnonymousUser):
        return None

    academy_ids = ProfileAcademy.objects.filter(user=request.user).values_list("academy__id", flat=True)

    kwargs = {}
    if matcher is None:
        kwargs["academy__id__in"] = academy_ids
    else:
        kwargs[matcher] = academy_ids

    logger.debug(f"Localizing academies: [{','.join([ str(i) for i in academy_ids])}]")
    # only cohorts from that academy
    query = query.filter(**kwargs)

    return query
