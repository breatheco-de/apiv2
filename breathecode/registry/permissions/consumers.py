import logging

from breathecode.admissions.actions import is_no_saas_student_up_to_date_in_any_cohort
from breathecode.authenticate.actions import get_user_language
from breathecode.authenticate.models import User
from breathecode.mentorship.models import MentorProfile, MentorshipService
from breathecode.payments.models import Consumable, ConsumptionSession
from breathecode.registry.models import Asset
from breathecode.utils.decorators import PermissionContextType
from breathecode.utils.i18n import translation
from breathecode.utils.validation_exception import ValidationException

logger = logging.getLogger(__name__)


def asset_by_slug(context: PermissionContextType, args: tuple, kwargs: dict) -> tuple[dict, tuple, dict]:

    context['will_consume'] = True
    request = context['request']

    lang = get_user_language(request)

    asset_slug = kwargs.get('asset_slug')
    academy_id = kwargs.get('academy_id')
    asset = Asset.get_by_slug(asset_slug, request)

    if asset is None or (asset.academy is not None and asset.academy.id != int(academy_id)):
        raise ValidationException(
            translation(lang,
                        en=f'Asset {asset_slug} not found for this academy',
                        es=f'El recurso {asset_slug} no existe para esta academia',
                        slug='asset-not-found'), 404)

    kwargs['asset'] = asset
    del kwargs['asset_slug']

    if is_no_saas_student_up_to_date_in_any_cohort(context['request'].user, academy=asset.academy) is False:
        context['consumables'] = Consumable.objects.none()
        context['will_consume'] = True
        return (context, args, kwargs)

    return (context, args, kwargs)
