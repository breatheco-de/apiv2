import logging

from django.db.models import Q

from breathecode.admissions.actions import is_no_saas_student_up_to_date_in_any_cohort
from breathecode.admissions.models import Academy, CohortUser
from breathecode.authenticate.actions import get_user_language
from breathecode.registry.models import Asset
from breathecode.utils.decorators import PermissionContextType
from breathecode.utils.i18n import translation
from breathecode.utils.payment_exception import PaymentException
from breathecode.utils.validation_exception import ValidationException

logger = logging.getLogger(__name__)


def asset_by_slug(context: PermissionContextType, args: tuple, kwargs: dict) -> tuple[dict, tuple, dict]:

    def count_cohorts(available_as_saas: bool) -> int:

        available_as_saas_bool = Q(cohort__available_as_saas=available_as_saas) | Q(
            cohort__available_as_saas=None, cohort__academy__available_as_saas=available_as_saas)
        return CohortUser.objects.filter(available_as_saas_bool,
                                         user=request.user,
                                         educational_status__in=['ACTIVE', 'GRADUATED'],
                                         cohort__academy__id=academy_id,
                                         cohort__syllabus_version__json__icontains=asset_slug).count()

    request = context['request']

    lang = get_user_language(request)

    asset_slug = kwargs.get('asset_slug')
    academy_id = kwargs.get('academy_id')
    asset = Asset.get_by_slug(asset_slug, request)
    academy = Academy.objects.filter(id=academy_id).first()

    if asset is None:
        raise ValidationException(
            translation(lang,
                        en=f'Asset {asset_slug} not found',
                        es=f'El recurso {asset_slug} no existe',
                        slug='asset-not-found'), 404)

    if count_cohorts(available_as_saas=False):
        context['will_consume'] = False

    else:
        context['will_consume'] = True

    kwargs['asset'] = asset
    kwargs['academy'] = academy
    del kwargs['asset_slug']
    del kwargs['academy_id']

    if context['will_consume'] is False and is_no_saas_student_up_to_date_in_any_cohort(context['request'].user,
                                                                                        academy=academy) is False:
        raise PaymentException(
            translation(lang,
                        en='You can\'t access this asset because your finantial status is not up to date',
                        es='No puedes acceder a este recurso porque tu estado financiero no está al dia',
                        slug='cohort-user-status-later'))

    return (context, args, kwargs)
