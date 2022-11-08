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

    bag.services.clear()
    bag.plans.clear()
    bag.token = None
    bag.expires_at = None

    services_not_found = set()
    plans_not_found = set()

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

    if isinstance(services, list):
        for service in services:
            bag.services.add(service)

    if isinstance(plans, list):
        for plan in plans:
            bag.plans.add(plan)

    bag.save()

    return bag


def get_amount(bag: Bag, academy: Academy, settings: UserSetting):
    amount = 0

    currency = settings.main_currency if academy.allowed_currencies.filter(
        code=settings.main_currency).exists() else academy.main_currency

    if not currency:
        currency, _ = Currency.objects.get_or_create(code='USD', name='United States dollar')

    for service in bag.services.all():
        p = service.service.prices.filter(currency=currency).first()
        if not p:
            bag.services.remove(service)
            continue

        amount += p.price

    for plan in bag.plans.all():
        p = plan.prices.filter(currency=currency).first()
        if not p:
            bag.plans.remove(plan)
            continue

        amount += p.price

    return amount
