from dateutil.relativedelta import relativedelta

from breathecode.admissions.models import Academy
from breathecode.authenticate.models import UserSetting
from breathecode.utils.i18n import translation
from breathecode.utils.validation_exception import ValidationException

from .models import Bag, Currency, Plan, ServiceItem, Subscription
from breathecode.utils import getLogger

logger = getLogger(__name__)


def calculate_renew_delta(subscription: Subscription):
    delta_args = {}
    if subscription.renew_every_unit == 'DAY':
        delta_args['days'] = subscription.renew_every

    elif subscription.renew_every_unit == 'WEEK':
        delta_args['weeks'] = subscription.renew_every

    elif subscription.renew_every_unit == 'MONTH':
        delta_args['months'] = subscription.renew_every

    elif subscription.renew_every_unit == 'YEAR':
        delta_args['years'] = subscription.renew_every

    return relativedelta(**delta_args)


def add_items_to_bag(request, settings: UserSetting, bag: Bag):
    services = request.data.get('services')
    plans = request.data.get('plans')
    cohorts = request.data.get('cohorts')

    bag.services.clear()
    bag.plans.clear()
    bag.token = None
    bag.expires_at = None

    services_not_found = set()
    plans_not_found = set()

    # get the plans related to a cohort
    if isinstance(cohorts, list):
        plan_ids = Plan.objects.filter(services__service__cohorts__id__in=cohorts).values_list('id',
                                                                                               flat=True)

        for plan_id in plan_ids:
            if not Plan.objects.filter(id=plan_id):
                plans_not_found.add(plan_id)

    if isinstance(services, list):
        for service in services:
            if not ServiceItem.objects.filter(id=service):
                services_not_found.add(service)

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

    if isinstance(cohorts, list):
        for plan_id in plan_ids:
            bag.plans.add(plan_id)

    if isinstance(services, list):
        for service in services:
            bag.services.add(service)

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

    for service_item in bag.services.all():
        if service_item.service.currency != currency:
            bag.services.remove(service_item)
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
