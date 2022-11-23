import ast
from functools import cache
from dateutil.relativedelta import relativedelta
from django.utils import timezone
from django.db.models.query_utils import Q

from breathecode.admissions.models import Academy, Cohort
from breathecode.authenticate.models import UserSetting
from breathecode.utils.i18n import translation
from breathecode.utils.validation_exception import ValidationException

from .models import Bag, Currency, Fixture, Plan, Service, ServiceItem, Subscription
from breathecode.utils import getLogger

logger = getLogger(__name__)


def calculate_relative_delta(unit: float, unit_type: str):
    delta_args = {}
    if unit_type == 'DAY':
        delta_args['days'] = unit

    elif unit_type == 'WEEK':
        delta_args['weeks'] = unit

    elif unit_type == 'MONTH':
        delta_args['months'] = unit

    elif unit_type == 'YEAR':
        delta_args['years'] = unit

    return relativedelta(**delta_args)


@cache
def get_fixture(academy_id: int, cohort_id: str, patterns: dict):
    cohorts = Cohort.objects.filter(Q(stage='INACTIVE') | Q(stage='PREWORK'),
                                    id=cohort_id,
                                    ending_date__gte=timezone.now(),
                                    academy__id=academy_id)

    # for pattern in [ast.literal_eval(p) for p in patterns['cohort'] if p]:
    for pattern in [p for p in patterns['cohort'] if p]:
        found = cohorts.filter(slug__regex=pattern)

        if found.exists():
            return patterns['id']

    return None


@cache
def get_fixture_patterns(academy_id: int):
    """
    Get the fixture patterns for the academy
    """

    fixtures = []

    for fixture in Fixture.objects.filter(cohort_pattern__isnull=False,
                                          academy__id=academy_id).values_list('id', 'cohort_pattern'):

        fixtures.append({'id': fixture[0], 'cohort': fixture[1]})

    return fixtures


def get_plans_belong_to_cohort(cohort):
    Fixture.objects.filter(cohorts__id=cohort.id)
    fixtures = cohort.fixture_set.filter(cohorts__id=cohort.id, cohorts__stage__in=['INACTIVE', 'PREWORK'])

    plans = Plan.objects.none()

    for fixture in fixtures:
        plans |= Plan.objects.filter(service_items__service=fixture.service)

    return plans


def add_items_to_bag(request, settings: UserSetting, bag: Bag):
    service_items = request.data.get('service_items')
    plans = request.data.get('plans')
    cohort_id = request.data.get('cohort')

    bag.service_items.clear()
    bag.plans.clear()
    bag.token = None
    bag.expires_at = None
    cohort_plans = []

    services_not_found = set()
    plans_not_found = set()

    if isinstance(service_items, list):
        for item in service_items:
            if not isinstance(item, dict):
                raise ValidationException(translation(settings.lang,
                                                      en='The service item needs to be a object',
                                                      es='El service item debe ser un objeto'),
                                          slug='service-item-not-object')

            if 'how_many' not in item or 'service' not in item or not isinstance(
                    item['how_many'], int) or not isinstance(item['service'], int):
                raise ValidationException(translation(
                    settings.lang,
                    en='The service item needs to have the keys of the integer type how_many and service',
                    es='El service item debe tener las llaves de tipo entero how_many y service'),
                                          slug='service-item-malformed')

    # get plan related to a cohort
    if cohort_id:
        try:
            cohort = Cohort.objects.get(id=int(cohort_id))
        except:
            raise ValidationException(translation(settings.lang,
                                                  en='Cohort not found',
                                                  es='Cohort no encontrada'),
                                      slug='cohort-not-found')

        cohort_plans = get_plans_belong_to_cohort(cohort)

        if not cohort_plans:
            raise ValidationException(translation(settings.lang,
                                                  en='Does not exists a fixture associated to this cohort',
                                                  es='No existe un accesorio asociado a esta cohorte'),
                                      slug='cohort-is-not-eligible')

        if len(cohort_plans) > 1:
            raise ValidationException(translation(
                settings.lang,
                en='Exists many plans associated to this cohort, can\'t be determined which one to use',
                es='No existe un accesorio asociado a esta cohorte'),
                                      slug='too-many-plans-associated-to-cohort')

    if isinstance(service_items, list):
        for service_item in service_items:
            if not Service.objects.filter(id=service_item['service']):
                services_not_found.add(service_item['service'])

    if isinstance(plans, list):
        for plan in plans:
            if not Plan.objects.filter(id=plan):
                plans_not_found.add(plan)

    if services_not_found or plans_not_found:
        raise ValidationException(translation(
            settings.lang,
            en=f'Items not found: services={services_not_found}, plans={plans_not_found}',
            es=f'Elementos no encontrados: servicios={services_not_found}, planes={plans_not_found}',
            slug='some-items-not-found'),
                                  code=404)

    if cohort_plans:
        bag.plans.add(*cohort_plans)

    if isinstance(service_items, list):
        for service_item in service_items:
            service = Service.objects.filter(id=service_item['service']).first()
            service_item, _ = ServiceItem.objects.get_or_create(service=service,
                                                                how_many=service_item['how_many'])
            bag.service_items.add(service_item)

    if isinstance(plans, list):
        for plan in plans:
            bag.plans.add(plan)

    bag.save()

    return bag


def get_amount(bag: Bag, academy: Academy, settings: UserSetting) -> tuple[float, float, float, float]:
    price_per_month = 0
    price_per_quarter = 0
    price_per_half = 0
    price_per_year = 0

    currency = academy.main_currency

    if not currency:
        currency, _ = Currency.objects.get_or_create(code='USD', name='United States dollar')

    for service_item in bag.service_items.all():
        if service_item.service.currency != currency:
            bag.service_items.remove(service_item)
            continue

        price_per_month += service_item.service.price_per_unit * service_item.how_many
        price_per_quarter += service_item.service.price_per_unit * service_item.how_many * 3
        price_per_half += service_item.service.price_per_unit * service_item.how_many * 6
        price_per_year += service_item.service.price_per_unit * service_item.how_many * 12

    for plan in bag.plans.all():
        if plan.currency != currency:
            bag.plans.remove(plan)
            continue

        price_per_month += plan.price_per_month
        price_per_quarter += plan.price_per_quarter
        price_per_half += plan.price_per_half
        price_per_year += plan.price_per_year

    return price_per_month, price_per_quarter, price_per_half, price_per_year
