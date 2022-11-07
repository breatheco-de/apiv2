from datetime import timedelta

from django.db.models.query_utils import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from breathecode.authenticate.actions import get_user_settings

from breathecode.payments import tasks
from breathecode.payments.models import (Bag, Consumable, Credit, Invoice, Plan, Service, ServiceItem,
                                         Subscription)
from breathecode.payments.serializers import (GetBagSerializer, GetConsumableSerializer, GetCreditSerializer,
                                              GetInvoiceSerializer, GetInvoiceSmallSerializer,
                                              GetPlanSerializer, GetServiceItemSerializer,
                                              GetServiceSerializer, GetSubscriptionSerializer,
                                              ServiceSerializer)
from breathecode.payments.services.stripe import Stripe
# from rest_framework.response import Response
from breathecode.utils import APIViewExtensions
from breathecode.utils.decorators.capable_of import capable_of
from breathecode.utils.i18n import translation
from breathecode.utils.payment_exception import PaymentException
from breathecode.utils.validation_exception import ValidationException


class PlanView(APIView):
    permission_classes = [AllowAny]
    extensions = APIViewExtensions(sort='-created_at', paginate=True)

    def get(self, request, plan_slug=None, service_slug=None):
        handler = self.extensions(request)
        settings = get_user_settings(request.user.id)

        if plan_slug:
            item = Plan.objects.filter(slug=plan_slug).first()
            if not item:
                raise ValidationException(translation(settings.lang,
                                                      en='Plan not found',
                                                      es='Plan no existe',
                                                      slug='not-found'),
                                          code=404)

            serializer = GetPlanSerializer(item, many=False)
            return handler.response(serializer.data)

        items = Plan.objects.filter(slug=plan_slug)

        if service_slug:
            items = items.filter(services__slug=service_slug)

        items = handler.queryset(items)
        serializer = GetPlanSerializer(items, many=True)

        return handler.response(serializer.data)


class AcademyPlanView(APIView):
    extensions = APIViewExtensions(sort='-created_at', paginate=True)

    @capable_of('read_plan')
    def get(self, request, plan_slug=None, service_slug=None, academy_id=None):
        handler = self.extensions(request)
        settings = get_user_settings(request.user.id)

        if plan_slug:
            item = Plan.objects.filter(Q(owner__id=academy_id) | Q(owner=None),
                                       slug=plan_slug).exclude(status='DELETED').first()
            if not item:
                raise ValidationException(translation(settings.lang,
                                                      en='Plan not found',
                                                      es='Plan no existe',
                                                      slug='not-found'),
                                          code=404)

            serializer = GetPlanSerializer(item, many=False)
            return handler.response(serializer.data)

        items = Plan.objects.filter(Q(owner__id=academy_id) | Q(owner=None)).exclude(status='DELETED')

        if service_slug:
            items = items.filter(services__slug=service_slug).exclude(status='DELETED')

        items = handler.queryset(items)
        serializer = GetPlanSerializer(items, many=True)

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
    def put(self, request, plan_id=None, academy_id=None):
        settings = get_user_settings(request.user.id)

        plan = Plan.objects.filter(Q(owner__id=academy_id) | Q(owner=None),
                                   id=plan_id).exclude(status='DELETED').first()
        if not plan:
            raise ValidationException(translation(settings.lang,
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
    def delete(self, request, plan_id=None, academy_id=None):
        settings = get_user_settings(request.user.id)

        plan = Plan.objects.filter(Q(owner__id=academy_id) | Q(owner=None),
                                   id=plan_id).exclude(status='DELETED').first()
        if not plan:
            raise ValidationException(translation(settings.lang,
                                                  en='Plan not found',
                                                  es='Plan no existe',
                                                  slug='not-found'),
                                      code=404)

        plan.status = 'DELETED'
        plan.save()

        return Response(status=status.HTTP_204_NO_CONTENT)


class ServiceView(APIView):
    permission_classes = [AllowAny]
    extensions = APIViewExtensions(sort='-created_at', paginate=True)

    def get(self, request, service_slug=None):
        handler = self.extensions(request)
        settings = get_user_settings(request.user.id)

        if service_slug:
            item = Service.objects.filter(slug=service_slug).first()

            if not item:
                raise ValidationException(translation(settings.lang,
                                                      en='Service not found',
                                                      es='No existe el Servicio',
                                                      slug='not-found'),
                                          code=404)

            serializer = GetServiceSerializer(item, many=False)
            return handler.response(serializer.data)

        items = Service.objects.filter()

        if group := request.GET.get('group'):
            items = items.filter(group__codename=group)

        if cohort_slug := request.GET.get('cohort_slug'):
            items = items.filter(cohorts__slug=cohort_slug)

        if mentorship_service_slug := request.GET.get('mentorship_service_slug'):
            items = items.filter(mentorship_services__slug=mentorship_service_slug)

        items = handler.queryset(items)
        serializer = GetServiceSerializer(items, many=True)

        return handler.response(serializer.data)


class AcademyServiceView(APIView):
    extensions = APIViewExtensions(sort='-created_at', paginate=True)

    @capable_of('read_service')
    def get(self, request, service_slug=None, academy_id=None):
        handler = self.extensions(request)
        settings = get_user_settings(request.user.id)

        if service_slug:
            item = Service.objects.filter(Q(owner__id=academy_id) | Q(owner=None) | Q(private=False),
                                          slug=service_slug).first()

            if not item:
                raise ValidationException(translation(settings.lang,
                                                      en='Service not found',
                                                      es='No existe el Servicio',
                                                      slug='not-found'),
                                          code=404)

            serializer = GetServiceSerializer(item, many=False)
            return handler.response(serializer.data)

        items = Service.objects.filter(Q(owner__id=academy_id) | Q(owner=None) | Q(private=False))

        if group := request.GET.get('group'):
            items = items.filter(group__codename=group)

        if cohort_slug := request.GET.get('cohort_slug'):
            items = items.filter(cohorts__slug=cohort_slug)

        if mentorship_service_slug := request.GET.get('mentorship_service_slug'):
            items = items.filter(mentorship_services__slug=mentorship_service_slug)

        items = handler.queryset(items)
        serializer = GetServiceSerializer(items, many=True)

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
        settings = get_user_settings(request.user.id)

        if not service:
            raise ValidationException(translation(settings.lang,
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
    extensions = APIViewExtensions(sort='-created_at', paginate=True)

    def get(self, request, service_slug=None):
        handler = self.extensions(request)

        items = ServiceItem.objects.filter()

        if service_slug:
            items = items.filter(service__slug=service_slug)

        if unit_type := request.GET.get('unit_type'):
            items = items.filter(unit_type=unit_type.split(','))

        items = handler.queryset(items)
        serializer = GetServiceItemSerializer(items, many=True)

        return handler.response(serializer.data)


class ConsumableView(APIView):
    extensions = APIViewExtensions(sort='-created_at', paginate=True)

    def get(self, request, service_slug=None):
        handler = self.extensions(request)
        utc_now = timezone.now()

        items = Consumable.objects.filter(Q(valid_until__gte=utc_now) | Q(valid_until=None),
                                          user=request.user).exclude(how_many=0)

        if service_slug:
            items = items.filter(services__slug=service_slug)

        if unit_type := request.GET.get('unit_type'):
            items = items.filter(unit_type=unit_type.split(','))

        items = handler.queryset(items)
        serializer = GetConsumableSerializer(items, many=True)

        return handler.response(serializer.data)


class CreditView(APIView):
    extensions = APIViewExtensions(sort='-created_at', paginate=True)

    def get(self, request, credit_id=None):
        handler = self.extensions(request)
        settings = get_user_settings(request.user.id)
        now = timezone.now()

        if credit_id:
            item = Credit.objects.filter(Q(valid_until__gte=now) | Q(valid_until=None),
                                         id=credit_id,
                                         invoice__user=request.user).first()

            if not item:
                raise ValidationException(translation(settings.lang,
                                                      en='Credit not found',
                                                      es='No existe el crédito',
                                                      slug='not-found'),
                                          code=404)

            serializer = GetCreditSerializer(items, many=True)
            return handler.response(serializer.data)

        items = Credit.objects.filter(Q(valid_until__gte=now) | Q(valid_until=None),
                                      invoice__user=request.user)

        if invoice_id := request.GET.get('invoice_id'):
            items = items.filter(invoice__id=invoice_id)

        if service_slug := request.GET.get('service_slug'):
            items = items.filter(services_slug=service_slug)

        items = handler.queryset(items)
        serializer = GetCreditSerializer(items, many=True)

        return handler.response(serializer.data)


class SubscriptionView(APIView):
    extensions = APIViewExtensions(sort='-created_at', paginate=True)

    def get(self, request, subscription_id=None):
        handler = self.extensions(request)
        settings = get_user_settings(request.user.id)
        now = timezone.now()

        if subscription_id:
            item = Subscription.objects.filter(
                Q(valid_until__gte=now) | Q(valid_until=None), id=subscription_id, user=request.user).exclude(
                    status='CANCELLED').exclude(status='DEPRECATED').exclude(status='PAYMENT_ISSUE').first()

            if not item:
                raise ValidationException(translation(settings.lang,
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
        settings = get_user_settings(request.user.id)
        now = timezone.now()

        if subscription_id:
            item = Subscription.objects.filter(
                Q(valid_until__gte=now) | Q(valid_until=None), id=subscription_id).exclude(
                    status='CANCELLED').exclude(status='DEPRECATED').exclude(status='PAYMENT_ISSUE').first()

            if not item:
                raise ValidationException(translation(settings.lang,
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


class InvoiceView(APIView):
    extensions = APIViewExtensions(sort='-created_at', paginate=True)

    def get(self, request, invoice_id=None):
        handler = self.extensions(request)
        settings = get_user_settings(request.user.id)
        now = timezone.now()

        if invoice_id:
            item = Invoice.objects.filter(id=invoice_id, user=request.user).first()

            if not item:
                raise ValidationException(translation(settings.lang,
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
        settings = get_user_settings(request.user.id)
        now = timezone.now()

        if invoice_id:
            item = Invoice.objects.filter(id=invoice_id, user=request.user, academy__id=academy_id).first()

            if not item:
                raise ValidationException(translation(settings.lang,
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

    def post(self, request):
        settings = get_user_settings(request.user.id)

        s = Stripe()
        s.add_contact(request.user)

        token = request.data.get('token')
        card_number = request.data.get('card_number')
        exp_month = request.data.get('exp_month')
        exp_year = request.data.get('exp_year')
        cvc = request.data.get('cvc')

        if not ((card_number and exp_month and exp_year and cvc) or token):
            raise ValidationException(translation(settings.lang,
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


def add_items_to_bag(request, bag):
    services = request.data.get('services')
    plans = request.data.get('plans')

    bag.services.clear()
    bag.plans.clear()
    bag.token = None
    bag.expires_at = None

    if isinstance(services, list):
        for service in services:
            bag.services.add(service)

    if isinstance(plans, list):
        for plan in plans:
            bag.plans.add(plan)

    bag.save()

    return bag


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
        request.data.get('')

        s = Stripe()
        s.add_contact(request.user)

        # do no show the bags of type preview they are build
        bag, _ = Bag.objects.get_or_create(user=request.user, status='CHECKING', type='BAG')
        add_items_to_bag(request, bag)

        serializer = GetBagSerializer(bag, many=False)
        return Response(serializer.data)

    def delete(self, request):
        # do no show the bags of type preview they are build
        Bag.objects.filter(user=request.user, status='CHECKING', type='BAG').delete()
        return Response(status=204)


class CheckingView(APIView):
    extensions = APIViewExtensions(sort='-created_at', paginate=True)

    def post(self, request):
        type = request.data.get('type', 'bag').upper()

        settings = get_user_settings(request.user.id)

        if type == 'BAG' and not (bag := Bag.objects.filter(user=request.user, status='CHECKING',
                                                            type=type).first()):
            raise ValidationException(translation(settings.lang,
                                                  en='Bag not found',
                                                  es='Bolsa no encontrada',
                                                  slug='not-found'),
                                      code=404)

        if type == 'PREVIEW':
            bag, _ = Bag.objects.get_or_create(user=request.user, status='CHECKING', type=type)
            add_items_to_bag(request, bag)

        utc_now = timezone.now()

        bag.token = Token.generate_key()
        bag.expires_at = utc_now + timedelta(minutes=10)

        #FIXME:
        handler = self.extensions(request)

        items = Bag.objects.filter(user=request.user)

        if status := request.GET.get('status'):
            items = items.filter(status__in=status.split(','))
        else:
            items = items.filter(status='CHECKING')

        items = handler.queryset(items)
        serializer = GetBagSerializer(items, many=True)

        return handler.response(serializer.data)


class PayView(APIView):
    extensions = APIViewExtensions(sort='-created_at', paginate=True)

    def post(self, request):
        utc_now = timezone.now()

        settings = get_user_settings(request.user.id)

        reputation = request.user.reputation.get_reputation()
        if reputation == 'FRAUD' or reputation == 'BAD':
            raise PaymentException(
                translation(
                    settings.lang,
                    en='the payment could not be completed because you have a bad reputation on this platform',
                    es='no se pudo completar el pago porque tienes mala reputación en esta plataforma',
                    slug='fraud-or-bad-reputation'))

        # do no show the bags of type preview they are build
        type = request.data.get('type', 'bag').upper()

        token = request.data.get('token', 'empty')
        recurrent = request.data.get('recurrent', False)
        bag = Bag.objects.filter(user=request.user,
                                 status='CHECKING',
                                 token=token,
                                 expires_at__gte=utc_now,
                                 type=type).first()
        if not bag:
            raise ValidationException(translation(settings.lang,
                                                  en='Bag not found or not have checking',
                                                  es='Bolsa no encontrada o sin checking',
                                                  slug='not-found-or-without-checking'),
                                      code=404)

        s = Stripe()
        #TODO: think about ban a user if have bad reputation (FinancialReputation)
        invoice = s.pay(request.user, bag.amount)

        bag.status = 'PAID'
        bag.is_recurrent = recurrent
        bag.token = None
        bag.expires_at = None
        bag.save()

        tasks.build_subscription.delay(bag.id, invoice.id)

        serializer = GetInvoiceSerializer(invoice, many=False)
        return Response(serializer.data)
