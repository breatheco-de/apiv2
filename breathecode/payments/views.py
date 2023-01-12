from datetime import timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from breathecode.admissions.models import Academy, Cohort
from breathecode.authenticate.actions import get_user_language, get_user_settings
from breathecode.events.models import EventType
from breathecode.mentorship.models import MentorshipService
from django.db.models import CharField, Q, Value

from breathecode.payments import tasks
from breathecode.admissions import tasks as admissions_tasks
from breathecode.payments.actions import (PlanFinder, add_items_to_bag, filter_consumables, get_amount,
                                          get_amount_by_chosen_period, get_balance_by_resource)
from breathecode.payments.models import (Bag, Consumable, FinancialReputation, Invoice, Plan, PlanFinancing,
                                         PlanServiceItem, Service, ServiceItem, Subscription)
from breathecode.payments.serializers import (GetBagSerializer, GetCreditSerializer, GetInvoiceSerializer,
                                              GetInvoiceSmallSerializer, GetPlanSerializer,
                                              GetServiceItemSerializer, GetServiceItemWithFeaturesSerializer,
                                              GetServiceSerializer, GetSubscriptionSerializer,
                                              ServiceSerializer)
from breathecode.payments.services.stripe import Stripe
from breathecode.utils import APIViewExtensions
from breathecode.utils.decorators.capable_of import capable_of
from breathecode.utils.generate_lookups_mixin import GenerateLookupsMixin
from breathecode.utils.i18n import translation
from breathecode.utils.payment_exception import PaymentException
from breathecode.utils.validation_exception import ValidationException
from django.db import IntegrityError, transaction
from breathecode.utils import getLogger

logger = getLogger(__name__)


class PlanView(APIView):
    permission_classes = [AllowAny]
    extensions = APIViewExtensions(sort='-id', paginate=True)

    def get(self, request, plan_slug=None, service_slug=None):
        handler = self.extensions(request)
        lang = get_user_language(request)

        if plan_slug:
            item = Plan.objects.filter(slug=plan_slug).first()
            if not item:
                raise ValidationException(translation(lang,
                                                      en='Plan not found',
                                                      es='Plan no existe',
                                                      slug='not-found'),
                                          code=404)

            serializer = GetPlanSerializer(item,
                                           many=False,
                                           context={'academy_id': request.GET.get('academy')},
                                           select=request.GET.get('select'))
            return handler.response(serializer.data)

        filtering = 'cohort' in request.GET or 'syllabus' in request.GET
        if 'cohort' in request.GET or 'syllabus' in request.GET:
            items = PlanFinder(request).get_plans_belongs_from_request()

        else:
            items = Plan.objects.filter()

        if not filtering and (is_onboarding := request.GET.get('is_onboarding', '').lower()):
            items = items.filter(is_onboarding=is_onboarding == 'true')

        items = items.exclude(status='DELETED')

        if service_slug:
            items = items.filter(services__slug=service_slug)

        items = handler.queryset(items)
        serializer = GetPlanSerializer(items,
                                       many=True,
                                       context={'academy_id': request.GET.get('academy')},
                                       select=request.GET.get('select'))

        return handler.response(serializer.data)


class AcademyPlanView(APIView):
    extensions = APIViewExtensions(sort='-created_at', paginate=True)

    @capable_of('read_plan')
    def get(self, request, plan_id=None, plan_slug=None, service_slug=None, academy_id=None):
        handler = self.extensions(request)
        lang = get_user_language(request)

        if plan_slug or plan_slug:
            item = Plan.objects.filter(Q(id=plan_id) | Q(slug=plan_slug),
                                       Q(owner__id=academy_id) | Q(owner=None),
                                       slug=plan_slug).exclude(status='DELETED').first()
            if not item:
                raise ValidationException(translation(lang,
                                                      en='Plan not found',
                                                      es='Plan no existe',
                                                      slug='not-found'),
                                          code=404)

            serializer = GetPlanSerializer(item,
                                           many=False,
                                           context={'academy_id': academy_id},
                                           select=request.GET.get('select'))
            return handler.response(serializer.data)

        filtering = 'cohort' in request.GET or 'syllabus' in request.GET
        if 'cohort' in request.GET or 'syllabus' in request.GET:
            items = PlanFinder(request).get_plans_belongs_from_request()

        else:
            items = Plan.objects.filter()

        if not filtering and (is_onboarding := request.GET.get('is_onboarding', '').lower()):
            items = items.filter(is_onboarding=is_onboarding == 'true')

        items = items.filter(Q(owner__id=academy_id) | Q(owner=None)).exclude(status='DELETED')

        if service_slug:
            items = items.filter(services__slug=service_slug).exclude(status='DELETED')

        items = handler.queryset(items)
        serializer = GetPlanSerializer(items,
                                       many=True,
                                       context={'academy_id': academy_id},
                                       select=request.GET.get('select'))

        return handler.response(serializer.data)

    @capable_of('crud_plan')
    def post(self, request, academy_id=None):
        data = request.data
        if not 'owner' in data or data['owner'] is not None:
            data['owner'] = academy_id

        serializer = ServiceSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=201)

    @capable_of('crud_plan')
    def put(self, request, plan_id=None, plan_slug=None, academy_id=None):
        lang = get_user_language(request)

        plan = Plan.objects.filter(Q(id=plan_id) | Q(slug=plan_slug),
                                   Q(owner__id=academy_id) | Q(owner=None),
                                   id=plan_id).exclude(status='DELETED').first()
        if not plan:
            raise ValidationException(translation(lang,
                                                  en='Plan not found',
                                                  es='Plan no existe',
                                                  slug='not-found'),
                                      code=404)

        data = request.data
        if not 'owner' in data or data['owner'] is not None:
            data['owner'] = academy_id

        serializer = ServiceSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)

    @capable_of('crud_plan')
    def delete(self, request, plan_id=None, plan_slug=None, academy_id=None):
        lang = get_user_language(request)

        plan = Plan.objects.filter(Q(id=plan_id) | Q(slug=plan_slug),
                                   Q(owner__id=academy_id) | Q(owner=None),
                                   id=plan_id).exclude(status='DELETED').first()
        if not plan:
            raise ValidationException(translation(lang,
                                                  en='Plan not found',
                                                  es='Plan no existe',
                                                  slug='not-found'),
                                      code=404)

        plan.status = 'DELETED'
        plan.save()

        return Response(status=status.HTTP_204_NO_CONTENT)


class AcademyPlanCohortView(APIView, GenerateLookupsMixin):
    extensions = APIViewExtensions(sort='-created_at', paginate=True)

    @capable_of('crud_plan')
    def put(self, request, plan_id=None, plan_slug=None, academy_id=None):
        lookups = self.generate_lookups(request, many_fields=['id', 'slug'])
        lang = get_user_language(request)

        if not (plan := Plan.objects.filter(Q(id=plan_id) | Q(slug=plan_slug),
                                            owner__id=academy_id).exclude(status='DELETED').first()):
            raise ValidationException(translation(lang,
                                                  en='Plan not found',
                                                  es='Plan no encontrado',
                                                  slug='not-found'),
                                      code=404)

        if not (cohort := Cohort.objects.filter(**lookups).first()):
            raise ValidationException(translation(lang,
                                                  en='Cohort not found',
                                                  es='Cohort no encontrada',
                                                  slug='cohort-not-found'),
                                      code=404)

        items = PlanServiceItem.objects.filter(plan=plan)

        for item in items:
            item.cohorts.clear()
            item.cohorts.add(cohort)

        return Response({'status': 'ok'}, status=status.HTTP_200_OK)


class ServiceView(APIView):
    permission_classes = [AllowAny]
    extensions = APIViewExtensions(sort='-created_at', paginate=True)

    def get(self, request, service_slug=None):
        handler = self.extensions(request)

        lang = get_user_language(request)

        if service_slug:
            item = Service.objects.filter(slug=service_slug).first()

            if not item:
                raise ValidationException(translation(lang,
                                                      en='Service not found',
                                                      es='No existe el Servicio',
                                                      slug='not-found'),
                                          code=404)

            serializer = GetServiceSerializer(item,
                                              many=False,
                                              context={'academy_id': request.GET.get('academy')},
                                              select=request.GET.get('select'))
            return handler.response(serializer.data)

        items = Service.objects.filter()

        if group := request.GET.get('group'):
            items = items.filter(group__codename=group)

        if cohort_slug := request.GET.get('cohort_slug'):
            items = items.filter(cohorts__slug=cohort_slug)

        if mentorship_service_slug := request.GET.get('mentorship_service_slug'):
            items = items.filter(mentorship_services__slug=mentorship_service_slug)

        items = handler.queryset(items)
        serializer = GetServiceSerializer(items,
                                          many=True,
                                          context={'academy_id': request.GET.get('academy')},
                                          select=request.GET.get('select'))

        return handler.response(serializer.data)


class AcademyServiceView(APIView):
    extensions = APIViewExtensions(sort='-created_at', paginate=True)

    @capable_of('read_service')
    def get(self, request, service_slug=None, academy_id=None):
        handler = self.extensions(request)
        lang = get_user_language(request)

        if service_slug:
            item = Service.objects.filter(Q(owner__id=academy_id) | Q(owner=None) | Q(private=False),
                                          slug=service_slug).first()

            if not item:
                raise ValidationException(translation(lang,
                                                      en='Service not found',
                                                      es='No existe el Servicio',
                                                      slug='not-found'),
                                          code=404)

            serializer = GetServiceSerializer(item,
                                              many=False,
                                              context={'academy_id': academy_id},
                                              select=request.GET.get('select'))
            return handler.response(serializer.data)

        items = Service.objects.filter(Q(owner__id=academy_id) | Q(owner=None) | Q(private=False))

        if group := request.GET.get('group'):
            items = items.filter(group__codename=group)

        if cohort_slug := request.GET.get('cohort_slug'):
            items = items.filter(cohorts__slug=cohort_slug)

        if mentorship_service_slug := request.GET.get('mentorship_service_slug'):
            items = items.filter(mentorship_services__slug=mentorship_service_slug)

        items = handler.queryset(items)
        serializer = GetServiceSerializer(items,
                                          many=True,
                                          context={'academy_id': academy_id},
                                          select=request.GET.get('select'))

        return handler.response(serializer.data)

    @capable_of('crud_service')
    def post(self, request, academy_id=None):
        data = request.data
        if not 'owner' in data or data['owner'] is not None:
            data['owner'] = academy_id

        serializer = ServiceSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of('crud_service')
    def put(self, request, service_slug=None, academy_id=None):
        service = Service.objects.filter(Q(owner__id=academy_id) | Q(owner=None), slug=service_slug).first()
        lang = get_user_language(request)

        if not service:
            raise ValidationException(translation(lang,
                                                  en='Service not found',
                                                  es='No existe el Servicio',
                                                  slug='not-found'),
                                      code=404)

        data = request.data
        if not 'owner' in data or data['owner'] is not None:
            data['owner'] = academy_id

        serializer = ServiceSerializer(service, data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ServiceItemView(APIView):
    permission_classes = [AllowAny]
    extensions = APIViewExtensions(sort='-id', paginate=True)

    def get(self, request, service_slug=None):
        handler = self.extensions(request)
        lang = get_user_language(request)

        items = ServiceItem.objects.none()

        if plan := request.GET.get('plan'):
            args = {'id': int(plan)} if plan.isnumeric() else {'slug': plan}

            p = Plan.objects.filter(**args).first()
            if not p:
                raise ValidationException(translation(lang,
                                                      en='Plan not found',
                                                      es='No existe el Plan',
                                                      slug='not-found'),
                                          code=404)

            items |= p.service_items.all()
            items = items.distinct()

        else:
            items = ServiceItem.objects.filter()

        if service_slug:
            items = items.filter(service__slug=service_slug)

        if unit_type := request.GET.get('unit_type'):
            items = items.filter(unit_type__in=unit_type.split(','))

        items = items.annotate(lang=Value(lang, output_field=CharField()))

        items = handler.queryset(items)
        serializer = GetServiceItemWithFeaturesSerializer(items, many=True)

        return handler.response(serializer.data)


class MeConsumableView(APIView):

    def get(self, request):
        utc_now = timezone.now()

        items = Consumable.objects.filter(Q(valid_until__gte=utc_now) | Q(valid_until=None),
                                          user=request.user)

        mentorship_services = MentorshipService.objects.none()
        mentorship_services = filter_consumables(request, items, mentorship_services, 'mentorship_service')

        cohorts = Cohort.objects.none()
        cohorts = filter_consumables(request, items, cohorts, 'cohort')

        event_types = EventType.objects.none()
        event_types = filter_consumables(request, items, event_types, 'event_type')

        balance = {
            'mentorship_services': get_balance_by_resource(mentorship_services, 'mentorship_service'),
            'cohorts': get_balance_by_resource(cohorts, 'cohort'),
            'event_types': get_balance_by_resource(event_types, 'event_type'),
        }

        return Response(balance)


class MeSubscriptionView(APIView):
    extensions = APIViewExtensions(sort='-created_at', paginate=True)

    def get(self, request, subscription_id=None):
        handler = self.extensions(request)
        lang = get_user_language(request)

        now = timezone.now()

        if subscription_id:
            item = Subscription.objects.filter(
                Q(valid_until__gte=now) | Q(valid_until=None), id=subscription_id, user=request.user).exclude(
                    status='CANCELLED').exclude(status='DEPRECATED').exclude(status='PAYMENT_ISSUE').first()

            if not item:
                raise ValidationException(translation(lang,
                                                      en='Subscription not found',
                                                      es='No existe el suscripción',
                                                      slug='not-found'),
                                          code=404)

            serializer = GetCreditSerializer(items, many=True)
            return handler.response(serializer.data)

        items = Subscription.objects.filter(Q(valid_until__gte=now) | Q(valid_until=None), user=request.user)

        if status := request.GET.get('status'):
            items = items.filter(status__in=status.split(','))
        else:
            items = items.exclude(status='CANCELLED').exclude(status='DEPRECATED').exclude(
                status='PAYMENT_ISSUE')

        if invoice_ids := request.GET.get('invoice_ids'):
            items = items.filter(invoices__id__in=invoice_ids.split(','))

        if service_slugs := request.GET.get('service_slugs'):
            items = items.filter(services__slug__in=service_slugs.split(','))

        if plan_slugs := request.GET.get('plan_slugs'):
            items = items.filter(plans__slug__in=plan_slugs.split(','))

        items = handler.queryset(items)
        serializer = GetSubscriptionSerializer(items, many=True)

        return handler.response(serializer.data)

    def post(self, request):
        handler = self.extensions(request)
        now = timezone.now()


class AcademySubscriptionView(APIView):

    extensions = APIViewExtensions(sort='-created_at', paginate=True)

    @capable_of('read_subscription')
    def get(self, request, subscription_id=None):
        handler = self.extensions(request)
        lang = get_user_language(request)

        now = timezone.now()

        if subscription_id:
            item = Subscription.objects.filter(
                Q(valid_until__gte=now) | Q(valid_until=None), id=subscription_id).exclude(
                    status='CANCELLED').exclude(status='DEPRECATED').exclude(status='PAYMENT_ISSUE').first()

            if not item:
                raise ValidationException(translation(lang,
                                                      en='Subscription not found',
                                                      es='No existe el suscripción',
                                                      slug='not-found'),
                                          code=404)

            serializer = GetSubscriptionSerializer(items, many=True)
            return handler.response(serializer.data)

        items = Subscription.objects.filter(Q(valid_until__gte=now) | Q(valid_until=None))

        if status := request.GET.get('status'):
            items = items.filter(status__in=status.split(','))
        else:
            items = items.exclude(status='CANCELLED').exclude(status='DEPRECATED').exclude(
                status='PAYMENT_ISSUE')

        if invoice_ids := request.GET.get('invoice_ids'):
            items = items.filter(invoices__id__in=invoice_ids.split(','))

        if service_slugs := request.GET.get('service_slugs'):
            items = items.filter(services__slug__in=service_slugs.split(','))

        if plan_slugs := request.GET.get('plan_slugs'):
            items = items.filter(plans__slug__in=plan_slugs.split(','))

        items = handler.queryset(items)
        serializer = GetSubscriptionSerializer(items, many=True)

        return handler.response(serializer.data)


class MeInvoiceView(APIView):
    extensions = APIViewExtensions(sort='-created_at', paginate=True)

    def get(self, request, invoice_id=None):
        handler = self.extensions(request)
        lang = get_user_language(request)

        if invoice_id:
            item = Invoice.objects.filter(id=invoice_id, user=request.user).first()

            if not item:
                raise ValidationException(translation(lang,
                                                      en='Invoice not found',
                                                      es='La factura no existe',
                                                      slug='not-found'),
                                          code=404)

            serializer = GetInvoiceSerializer(items, many=True)
            return handler.response(serializer.data)

        items = Invoice.objects.filter(user=request.user)

        if status := request.GET.get('status'):
            items = items.filter(status__in=status.split(','))

        items = handler.queryset(items)
        serializer = GetInvoiceSmallSerializer(items, many=True)

        return handler.response(serializer.data)


class AcademyInvoiceView(APIView):
    extensions = APIViewExtensions(sort='-created_at', paginate=True)

    @capable_of('read_invoice')
    def get(self, request, invoice_id=None, academy_id=None):
        handler = self.extensions(request)
        lang = get_user_language(request)

        if invoice_id:
            item = Invoice.objects.filter(id=invoice_id, user=request.user, academy__id=academy_id).first()

            if not item:
                raise ValidationException(translation(lang,
                                                      en='Invoice not found',
                                                      es='La factura no existe',
                                                      slug='not-found'),
                                          code=404)

            serializer = GetInvoiceSerializer(items, many=True)
            return handler.response(serializer.data)

        items = Invoice.objects.filter(user=request.user, academy__id=academy_id)

        if status := request.GET.get('status'):
            items = items.filter(status__in=status.split(','))

        items = handler.queryset(items)
        serializer = GetInvoiceSmallSerializer(items, many=True)

        return handler.response(serializer.data)


class CardView(APIView):
    extensions = APIViewExtensions(sort='-created_at', paginate=True)

    def post(self, request):
        lang = get_user_language(request)

        s = Stripe()
        s.set_language(lang)
        s.add_contact(request.user)

        token = request.data.get('token')
        card_number = request.data.get('card_number')
        exp_month = request.data.get('exp_month')
        exp_year = request.data.get('exp_year')
        cvc = request.data.get('cvc')

        if not ((card_number and exp_month and exp_year and cvc) or token):
            raise ValidationException(translation(lang,
                                                  en='Missing card information',
                                                  es='Falta la información de la tarjeta',
                                                  slug='missing-card-information'),
                                      code=404)

        if not token:
            #TODO: this throw a exception
            token = s.create_card_token(card_number, exp_month, exp_year, cvc)

        #TODO: this throw a exception
        s.add_payment_method(request.user, token)
        return Response({'status': 'ok'})


class BagView(APIView):
    extensions = APIViewExtensions(sort='-created_at', paginate=True)

    def get(self, request):
        handler = self.extensions(request)

        # do no show the bags of type preview they are build
        items = Bag.objects.filter(user=request.user, type='BAG')

        if status := request.GET.get('status'):
            items = items.filter(status__in=status.split(','))
        else:
            items = items.filter(status='CHECKING')

        items = handler.queryset(items)
        serializer = GetBagSerializer(items, many=True)

        return handler.response(serializer.data)

    def put(self, request):
        handler = self.extensions(request)
        language = handler.language.get()

        settings = get_user_settings(request.user.id)
        language = language or settings.lang or 'en'

        s = Stripe()
        s.set_language(language)
        s.add_contact(request.user)

        # do no show the bags of type preview they are build
        bag, _ = Bag.objects.get_or_create(user=request.user, status='CHECKING', type='BAG')
        add_items_to_bag(request, settings, bag)

        serializer = GetBagSerializer(bag, many=False)
        return Response(serializer.data)

    def delete(self, request):
        # do no show the bags of type preview they are build
        Bag.objects.filter(user=request.user, status='CHECKING', type='BAG').delete()
        return Response(status=204)


class CheckingView(APIView):
    extensions = APIViewExtensions(sort='-created_at', paginate=True)

    def put(self, request):
        bag_type = request.data.get('type', 'BAG').upper()
        created = False

        settings = get_user_settings(request.user.id)

        with transaction.atomic():
            sid = transaction.savepoint()
            try:
                if bag_type == 'BAG' and not (bag := Bag.objects.filter(
                        user=request.user, status='CHECKING', type=bag_type).first()):
                    raise ValidationException(translation(settings.lang,
                                                          en='Bag not found',
                                                          es='Bolsa no encontrada',
                                                          slug='not-found'),
                                              code=404)
                if bag_type == 'PREVIEW':
                    academy = request.data.get('academy')
                    kwargs = {}

                    if academy and (isinstance(academy, int) or academy.isnumeric()):
                        kwargs['id'] = int(academy)
                    else:
                        kwargs['slug'] = academy

                    academy = Academy.objects.filter(main_currency__isnull=False, **kwargs).first()

                    if not academy:
                        cohort = request.data.get('cohort')

                        kwargs = {}

                        if cohort and (isinstance(cohort, int) or cohort.isnumeric()):
                            kwargs['id'] = int(cohort)
                        else:
                            kwargs['slug'] = cohort

                        cohort = Cohort.objects.filter(academy__main_currency__isnull=False, **kwargs).first()
                        if cohort:
                            academy = cohort.academy

                    if not academy:
                        raise ValidationException(translation(
                            settings.lang,
                            en='Academy not found or not configured properly',
                            es='Academia no encontrada o no configurada correctamente',
                            slug='not-found'),
                                                  code=404)

                    bag, created = Bag.objects.get_or_create(user=request.user,
                                                             status='CHECKING',
                                                             type=bag_type,
                                                             academy=academy,
                                                             currency=academy.main_currency)
                    add_items_to_bag(request, settings, bag)

                utc_now = timezone.now()

                bag.token = Token.generate_key()
                bag.expires_at = utc_now + timedelta(minutes=60)

                plan = bag.plans.filter(status='CHECKING').first()

                #FIXME: the service items should be bought without renewals
                if not plan or plan.is_renewable:
                    bag.amount_per_month, bag.amount_per_quarter, bag.amount_per_half, bag.amount_per_year = get_amount(
                        bag, bag.academy.main_currency)

                amount = bag.amount_per_month or bag.amount_per_quarter or bag.amount_per_half or bag.amount_per_year
                plans = bag.plans.all()
                if not amount and plans.filter(financing_options__id__gte=1):
                    amount = 1

                if amount == 0 and PlanFinancing.objects.filter(plans__in=plans).count():
                    raise ValidationException(translation(settings.lang,
                                                          en='Your free trial was already took',
                                                          es='Tu prueba gratuita ya fue tomada',
                                                          slug='your-free-trial-was-already-took'),
                                              code=400)

                bag.save()
                transaction.savepoint_commit(sid)

                serializer = GetBagSerializer(bag, many=False)
                return Response(serializer.data,
                                status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

            except Exception as e:
                transaction.savepoint_rollback(sid)
                raise e


class PayView(APIView):
    extensions = APIViewExtensions(sort='-created_at', paginate=True)

    def post(self, request):
        utc_now = timezone.now()
        lang = get_user_language(request)

        with transaction.atomic():
            sid = transaction.savepoint()
            try:

                reputation, _ = FinancialReputation.objects.get_or_create(user=request.user)

                current_reputation = reputation.get_reputation()
                if current_reputation == 'FRAUD' or current_reputation == 'BAD':
                    raise PaymentException(
                        translation(
                            lang,
                            en=
                            'The payment could not be completed because you have a bad reputation on this platform',
                            es='No se pudo completar el pago porque tienes mala reputación en esta plataforma',
                            slug='fraud-or-bad-reputation'))

                # do no show the bags of type preview they are build
                # type = request.data.get('type', 'BAG').upper()
                token = request.data.get('token')
                if not token:
                    raise ValidationException(translation(lang,
                                                          en='Invalid bag token',
                                                          es='El token de la bolsa es inválido',
                                                          slug='missing-token'),
                                              code=404)

                recurrent = request.data.get('recurrent', False)
                bag = Bag.objects.filter(user=request.user,
                                         status='CHECKING',
                                         token=token,
                                         academy__main_currency__isnull=False,
                                         expires_at__gte=utc_now).first()

                if not bag:
                    raise ValidationException(translation(
                        lang,
                        en='Bag not found, maybe you need to renew the checking',
                        es='Bolsa no encontrada, quizás necesitas renovar el checking',
                        slug='not-found-or-without-checking'),
                                              code=404)

                if bag.service_items.count() == 0 and bag.plans.count() == 0:
                    raise ValidationException(translation(lang,
                                                          en='Bag is empty',
                                                          es='La bolsa esta vacía',
                                                          slug='bag-is-empty'),
                                              code=400)

                how_many_installments = request.data.get('how_many_installments')
                chosen_period = request.data.get('chosen_period', '').upper()
                if not how_many_installments and not chosen_period:
                    raise ValidationException(translation(lang,
                                                          en='Missing chosen period',
                                                          es='Falta el periodo elegido',
                                                          slug='missing-chosen-period'),
                                              code=400)

                if not how_many_installments and chosen_period not in ['MONTH', 'QUARTER', 'HALF', 'YEAR']:
                    raise ValidationException(translation(lang,
                                                          en='Invalid chosen period',
                                                          es='Periodo elegido inválido',
                                                          slug='invalid-chosen-period'),
                                              code=400)

                if not chosen_period and (not isinstance(how_many_installments, int)
                                          or how_many_installments <= 0):
                    raise ValidationException(translation(
                        lang,
                        en='how_many_installments must be a positive number greather than 0',
                        es='how_many_installments debe ser un número positivo mayor a 0',
                        slug='invalid-how-many-installments'),
                                              code=400)

                if not chosen_period and how_many_installments:
                    bag.how_many_installments = how_many_installments

                if bag.how_many_installments > 0:
                    try:
                        plan = bag.plans.filter().first()
                        option = plan.financing_options.filter(
                            how_many_months=bag.how_many_installments).first()
                        amount = option.monthly_price
                    except:
                        raise ValidationException(translation(
                            lang,
                            en='Bag bad configured, related to financing option',
                            es='La bolsa esta mal configurada, relacionado a la opción de financiamiento',
                            slug='invalid-bag-configured-by-installments'),
                                                  code=500)
                else:
                    amount = get_amount_by_chosen_period(bag, chosen_period)

                if amount == 0 and PlanFinancing.objects.filter(plans__in=bag.plans.all()).count():
                    raise ValidationException(translation(lang,
                                                          en='Your free trial was already took',
                                                          es='Tu prueba gratuita ya fue tomada',
                                                          slug='your-free-trial-was-already-took'),
                                              code=500)

                if amount > 0:
                    s = Stripe()
                    s.set_language(lang)
                    invoice = s.pay(request.user, bag, amount, currency=bag.currency.code)

                else:
                    invoice = Invoice(amount=0,
                                      paid_at=utc_now,
                                      user=request.user,
                                      bag=bag,
                                      academy=bag.academy,
                                      status='FULFILLED',
                                      currency=bag.academy.main_currency)

                    invoice.save()

                bag.chosen_period = chosen_period or 'MONTH'
                bag.status = 'PAID'
                bag.is_recurrent = recurrent
                bag.token = None
                bag.expires_at = None
                bag.save()

                transaction.savepoint_commit(sid)

                if amount == 0:
                    tasks.build_free_trial.delay(bag.id, invoice.id)

                elif bag.how_many_installments > 0:

                    tasks.build_plan_financing.delay(bag.id, invoice.id)
                else:
                    tasks.build_subscription.delay(bag.id, invoice.id)

                for cohort in bag.selected_cohorts.all():
                    admissions_tasks.build_cohort_user.delay(cohort.id, bag.user.id)

                serializer = GetInvoiceSerializer(invoice, many=False)
                return Response(serializer.data, status=201)

            except Exception as e:
                transaction.savepoint_rollback(sid)
                raise e
