import logging

from breathecode.admissions.actions import is_no_saas_student_up_to_date_in_any_cohort
from breathecode.payments.models import Consumable
from breathecode.utils.decorators import PermissionContextType

logger = logging.getLogger(__name__)


def code_revision_service(context: PermissionContextType, args: tuple, kwargs: dict) -> tuple[dict, tuple, dict]:

    if is_no_saas_student_up_to_date_in_any_cohort(context['request'].user) is False:
        context['consumables'] = Consumable.objects.none()
        context['will_consume'] = True
        return (context, args, kwargs)

    context['consumables'] = context['consumables'].filter(service_set__slug='code_revision')
    return (context, args, kwargs)
