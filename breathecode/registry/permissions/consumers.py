import logging

from django.db.models import Q

from breathecode.admissions.actions import is_no_saas_student_up_to_date_in_any_cohort
from breathecode.admissions.models import Cohort, CohortUser
from breathecode.authenticate.actions import get_user_language
from breathecode.registry.models import Asset
from breathecode.utils.decorators import PermissionContextType
from breathecode.utils.i18n import translation
from breathecode.utils.payment_exception import PaymentException
from breathecode.utils.validation_exception import ValidationException

logger = logging.getLogger(__name__)


def asset_by_slug(context: PermissionContextType, args: tuple, kwargs: dict) -> tuple[dict, tuple, dict]:

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

    #############

    no_available_as_saas = Q(cohort__available_as_saas=False) | Q(cohort__available_as_saas=None,
                                                                  cohort__academy__available_as_saas=False)
    cu = CohortUser.objects.filter(no_available_as_saas,
                                   user=request.user,
                                   educational_status__in=['ACTIVE', 'GRADUATED'],
                                   cohort__academy=asset.academy).first()

    cohort = cu.cohort if cu else None
    if cohort is None:
        context['will_consume'] = asset.academy.available_as_saas

    elif cohort.available_as_saas is False or cohort.available_as_saas is None and asset.academy.available_as_saas is False:
        context['will_consume'] = False

    else:
        context['will_consume'] = True

    kwargs['asset'] = asset
    del kwargs['asset_slug']

    if context['will_consume'] is False and is_no_saas_student_up_to_date_in_any_cohort(context['request'].user,
                                                                                        academy=asset.academy) is False:
        raise PaymentException(
            translation(lang,
                        en=f'You can\'t access this asset because you finantial status is not up to date',
                        es=f'No puedes acceder a este recurso porque tu estado financiero no está al dia',
                        slug='cohort-user-status-later'))

    return (context, args, kwargs)
