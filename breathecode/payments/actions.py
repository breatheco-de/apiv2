import ast
from functools import cache
import re
from typing import Optional, Type
from dateutil.relativedelta import relativedelta
from django.utils import timezone
from django.db.models.query_utils import Q
from django.db.models import Sum, QuerySet
from django.core.handlers.wsgi import WSGIRequest
from pytz import UTC

from breathecode.admissions.models import Academy, Cohort, CohortUser, Syllabus
from breathecode.authenticate.actions import get_user_settings
from breathecode.authenticate.models import UserSetting
from breathecode.utils.attr_dict import AttrDict
from breathecode.utils.i18n import translation
from breathecode.utils.validation_exception import ValidationException
from rest_framework.request import Request

from .models import SERVICE_UNITS, Bag, Consumable, Currency, Plan, Service, ServiceItem, Subscription
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


class PlanFinder:
    cohort: Optional[Cohort] = None
    syllabus: Optional[Syllabus] = None

    def __init__(self, request: Request, lang: Optional[str] = None) -> None:
        self.request = request

        if lang:
            self.lang = lang

        else:
            self.lang = request.META.get('HTTP_ACCEPT_LANGUAGE')

        if not self.lang and request.user.id:
            settings = get_user_settings(request.user.id)
            self.lang = settings.lang

        if not self.lang:
            self.lang = 'en'

        self.academy_slug = request.GET.get('academy') or request.data.get('academy')

        if cohort := request.GET.get('cohort') or request.data.get('cohort'):
            self.cohort = self._get_instance(Cohort, cohort, self.academy_slug)

        if syllabus := request.GET.get('syllabus') or request.data.get('syllabus'):
            self.syllabus = self._get_instance(Syllabus, syllabus, self.academy_slug)

    def _get_pk(self, pk):
        if isinstance(pk, int) or pk.isnumeric():
            return int(pk)

        return 0

    def _get_instance(self,
                      model: Type[Cohort | Syllabus],
                      pk: str,
                      academy: Optional[str] = None) -> Optional[Cohort | Syllabus]:
        args = []
        kwargs = {}

        if isinstance(pk, int) or pk.isnumeric():
            kwargs['id'] = int(pk)
        else:
            kwargs['slug'] = pk

        if academy and model == Syllabus:
            args.append(
                Q(academy_owner__slug=academy) | Q(academy_owner__id=self._get_pk(academy))
                | Q(private=False))

        elif academy and model == Cohort:
            args.append(Q(academy__slug=academy) | Q(academy__id=self._get_pk(academy)))

        resource = model.objects.filter(*args, **kwargs).first()
        if not resource:
            raise ValidationException(
                translation(self.lang,
                            en=f'{model.__name__} not found',
                            es=f'{model.__name__} no encontrada',
                            slug=f'{model.__name__.lower()}-not-found'))

        return resource

    def _cohort_handler(self, on_boarding: Optional[bool] = None, auto: bool = False):
        additional_args = {}

        if on_boarding is not None:
            additional_args['is_onboarding'] = on_boarding

        if not self.cohort.syllabus_version:
            return Plan.objects.none()

        if not additional_args and auto:
            additional_args['is_onboarding'] = not CohortUser.objects.filter(
                cohort__syllabus_version__syllabus=self.cohort.syllabus_version.syllabus).exists()

        plans = Plan.objects.filter(planserviceitem__cohorts__id=self.cohort.id,
                                    planserviceitem__cohorts__stage__in=['INACTIVE', 'PREWORK'],
                                    **additional_args).distinct()

        return plans

    def _syllabus_handler(self, on_boarding: Optional[bool] = None, auto: bool = False):
        additional_args = {}

        if on_boarding is not None:
            additional_args['is_onboarding'] = on_boarding

        if not additional_args and auto:
            additional_args['is_onboarding'] = not CohortUser.objects.filter(
                cohort__syllabus_version__syllabus=self.syllabus).exists()

        plans = Plan.objects.filter(planserviceitem__cohorts__syllabus_version__syllabus=self.syllabus,
                                    planserviceitem__cohorts__stage__in=['INACTIVE', 'PREWORK'],
                                    **additional_args).distinct()

        return plans

    def get_plans_belongs(self, on_boarding: Optional[bool] = None, auto: bool = False):
        if self.syllabus:
            return self._syllabus_handler(on_boarding, auto)

        if self.cohort:
            return self._cohort_handler(on_boarding, auto)

        raise NotImplementedError('Resource handler not implemented')

    def get_plans_belongs_from_request(self):
        is_onboarding = self.request.data.get('is_onboarding') or self.request.GET.get('is_onboarding')

        additional_args = {}

        if is_onboarding:
            additional_args['is_onboarding'] = is_onboarding

        if not additional_args:
            additional_args['auto'] = True

        return self.get_plans_belongs(**additional_args)


def add_items_to_bag(request, settings: UserSetting, bag: Bag):
    service_items = request.data.get('service_items')
    plans = request.data.get('plans')
    cohorts = request.data.get('cohort')

    bag.service_items.clear()
    bag.plans.clear()
    bag.token = None
    bag.expires_at = None

    services_not_found = set()
    plans_not_found = set()
    cohorts_not_found = set()

    cohort_ids = []

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

    if isinstance(service_items, list):
        for service_item in service_items:
            kwargs = {}

            if service_item['service'] and (isinstance(service_item['service'], int)
                                            or service_item['service'].isnumeric()):
                kwargs['id'] = int(service_item['service'])
            else:
                kwargs['slug'] = service_item['service']

            if not Service.objects.filter(**kwargs):
                services_not_found.add(service_item['service'])

    if isinstance(cohorts, list):
        for cohort in cohorts:
            kwargs = {}

            if isinstance(cohort, int) or cohort.isnumeric():
                kwargs['id'] = int(cohort)

            else:
                kwargs['slug'] = cohort

            if c := Cohort.objects.filter(**kwargs).first():
                cohort_ids.append(c.id)

            if not c:
                cohorts_not_found.add(cohort)

    if isinstance(plans, list):
        for plan in plans:
            kwargs = {}

            if plan and (isinstance(plan, int) or plan.isnumeric()):
                kwargs['id'] = int(plan)
            else:
                kwargs['slug'] = plan

            if not Plan.objects.filter(**kwargs):
                plans_not_found.add(plan)

    if services_not_found or plans_not_found or plans_not_found:
        raise ValidationException(translation(
            settings.lang,
            en=f'Items not found: services={services_not_found}, plans={plans_not_found}, '
            f'cohorts={cohorts_not_found}',
            es=f'Elementos no encontrados: servicios={services_not_found}, planes={plans_not_found}, '
            f'cohortes={cohorts_not_found}',
            slug='some-items-not-found'),
                                  code=404)

    too_many_cohorts_error = translation(settings.lang,
                                         en='You can only select one cohort',
                                         es='Solo puedes seleccionar una cohorte',
                                         slug='more-than-one-cohort-selected')

    if len(cohort_ids) > 1:
        raise ValidationException(too_many_cohorts_error, code=400)

    if isinstance(service_items, list):
        for service_item in service_items:
            kwargs = {}

            if service_item['service'] and (isinstance(service_item['service'], int)
                                            or service_item['service'].isnumeric()):
                kwargs['id'] = int(service_item['service'])
            else:
                kwargs['slug'] = service_item['service']

            service = Service.objects.filter(**kwargs).first()
            service_item, _ = ServiceItem.objects.get_or_create(service=service,
                                                                how_many=service_item['how_many'])
            bag.service_items.add(service_item)

    if isinstance(plans, list):
        for plan in plans:
            kwargs = {}

            if plan and (isinstance(plan, int) or plan.isnumeric()):
                kwargs['id'] = int(plan)
            else:
                kwargs['slug'] = plan

            p = Plan.objects.filter(**kwargs).first()
            bag.plans.add(p)

    how_many_plans = bag.plans.count()
    if how_many_plans > 1:
        raise ValidationException(too_many_cohorts_error, code=400)

    for cohort in cohort_ids:
        #FIXME: this is not working with two cohorts yet
        if not bag.plans.filter(schedulers__cohorts__id=cohort).exists():
            raise ValidationException(translation(
                settings.lang,
                en='The selected cohort is not available for the selected plan',
                es='La cohorte seleccionada no está disponible para el plan seleccionado',
                slug='cohort-not-available-for-plan'),
                                      code=400)

        bag.selected_cohorts.add(cohort)

    if how_many_plans == 1 and bag.service_items.count():
        raise ValidationException(translation(settings.lang,
                                              en="You can't select a plan and a services at the same time",
                                              es='No puedes seleccionar un plan y servicios al mismo tiempo',
                                              slug='one-plan-and-many-services'),
                                  code=400)

    bag.save()

    return bag


def get_amount(bag: Bag, currency: Currency) -> tuple[float, float, float, float]:
    price_per_month = 0
    price_per_quarter = 0
    price_per_half = 0
    price_per_year = 0

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


def get_amount_by_chosen_period(bag: Bag, chosen_period: str):

    if chosen_period == 'MONTH':
        amount = bag.amount_per_month

    if chosen_period == 'QUARTER':
        amount = bag.amount_per_quarter

        if not amount:
            amount = bag.amount_per_month * 3

    if chosen_period == 'HALF':
        amount = bag.amount_per_half

        if not amount:
            amount = bag.amount_per_quarter * 2

        if not amount:
            amount = bag.amount_per_month * 6

    if chosen_period == 'YEAR':
        amount = bag.amount_per_year

        if not amount:
            amount = bag.amount_per_half * 2

        if not amount:
            amount = bag.amount_per_quarter * 4

        if not amount:
            amount = bag.amount_per_month * 12

    return amount


def get_chosen_period_from_subscription(subscription: Subscription, settings: Optional[UserSetting] = None):
    how_many = subscription.pay_every
    unit = subscription.pay_every_unit

    if not settings:
        settings = get_user_settings(subscription.user.id)

    if unit == 'MONTH' and how_many == 1:
        return 'MONTH'

    if unit == 'MONTH' and how_many == 3:
        return 'QUARTER'

    if unit == 'MONTH' and how_many == 6:
        return 'HALF'

    if (unit == 'MONTH' and how_many == 12) or (unit == 'YEAR' and how_many == 1):
        return 'YEAR'

    raise Exception(
        translation(settings.lang,
                    en=f'Period not found for pay_every_unit={unit} and pay_every={how_many}',
                    es=f'Periodo no encontrado para pay_every_unit={unit} and pay_every={how_many}',
                    slug='cannot-determine-period'))


def get_bag_from_subscription(subscription: Subscription, settings: Optional[UserSetting] = None) -> Bag:
    bag = Bag()

    if not settings:
        settings = get_user_settings(subscription.user.id)

    last_invoice = subscription.invoices.filter().last()
    if not last_invoice:
        raise Exception(
            translation(settings.lang,
                        en='Invalid subscription, this has no invoices',
                        es='Suscripción invalida, esta no tiene facturas',
                        slug='subscription-has-no-invoices'))

    chosen_period = get_chosen_period_from_subscription(subscription, settings)

    bag.status = 'RENEWAL'
    bag.type = 'BAG'
    bag.academy = subscription.academy
    bag.currency = last_invoice.currency
    bag.user = subscription.user
    bag.is_recurrent = True
    bag.chosen_period = chosen_period
    bag.save()

    for service_item in subscription.service_items.all():
        bag.service_items.add(service_item)

    for plan in subscription.plans.all():
        bag.plans.add(plan)

    bag.amount_per_month, bag.amount_per_quarter, bag.amount_per_half, bag.amount_per_year = get_amount(
        bag, last_invoice.currency)

    #
    bag.save()

    return bag


def filter_consumables(request: WSGIRequest, items: QuerySet[Consumable], queryset: QuerySet, key: str):
    if ids := request.GET.get(key):
        try:
            ids = [int(x) for x in ids.split(',')]
        except:
            raise ValidationException(f'{key} param must be integer')

        queryset |= items.filter(**{f'{key}__id__in': ids})

    if slugs := request.GET.get(f'{key}_slug'):
        slugs = slugs.split(',')
        queryset |= items.filter(**{f'{key}__slug__in': slugs})

    queryset = queryset.distinct()
    return queryset


def get_balance_by_resource(queryset: QuerySet, key: str):
    result = []

    ids = {getattr(x, key).id for x in queryset}
    for id in ids:
        current = queryset.filter(**{f'{key}__id': id})
        instance = current.first()
        balance = {}
        items = []
        units = {x[0] for x in SERVICE_UNITS}
        for unit in units:
            per_unit = current.filter(unit_type=unit)
            balance[unit.lower()] = -1 if per_unit.filter(
                how_many=-1).exists() else per_unit.aggregate(Sum('how_many'))['how_many__sum']

        for x in queryset:
            valid_until = x.valid_until
            if valid_until:
                valid_until = re.sub(r'\+00:00$', 'Z', valid_until.replace(tzinfo=UTC).isoformat())

            items.append({
                'id': x.id,
                'how_many': x.how_many,
                'unit_type': x.unit_type,
                'valid_until': x.valid_until,
            })

        result.append({
            'id': getattr(instance, key).id,
            'slug': getattr(instance, key).slug,
            'balance': balance,
            'items': items,
        })
    return result
