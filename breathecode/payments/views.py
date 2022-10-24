from rest_framework.views import APIView
from breathecode.payments.models import Consumable, Credit, Invoice, Plan, Service, ServiceItem, Subscription
from breathecode.payments.serializers import (GetConsumableSerializer, GetCreditSerializer,
                                              GetInvoiceSerializer, GetInvoiceSmallSerializer,
                                              GetPlanSerializer, GetServiceItemSerializer,
                                              GetServiceSerializer, GetSubscriptionSerializer,
                                              ServiceSerializer)
# from rest_framework.response import Response
from breathecode.utils import APIViewExtensions
from rest_framework.permissions import AllowAny
from django.db.models.query_utils import Q
from django.utils import timezone
from rest_framework.response import Response
from breathecode.utils.decorators.capable_of import capable_of
from rest_framework import status

from breathecode.utils.validation_exception import ValidationException


class PlanView(APIView):
    permission_classes = [AllowAny]
    extensions = APIViewExtensions(sort='-created_at', paginate=True)

    def get(self, request, plan_slug=None, service_slug=None):
        handler = self.extensions(request)

        if plan_slug:
            item = Plan.objects.filter(slug=plan_slug).first()
            if not item:
                raise ValidationException('Plan not found', code=404, slug='not-found')

            serializer = GetPlanSerializer(item, many=False)
            return handler.response(serializer.data)

        items = Plan.objects.filter(slug=plan_slug)

        if service_slug:
            items = items.filter(services__slug=service_slug)

        items = handler.queryset(items)
        serializer = GetPlanSerializer(items, many=True)

        return handler.response(serializer.data)


class AcademyPlanView(APIView):
    permission_classes = [AllowAny]
    extensions = APIViewExtensions(sort='-created_at', paginate=True)

    @capable_of('read_plan')
    def get(self, request, plan_slug=None, service_slug=None, academy_id=None):
        handler = self.extensions(request)

        if plan_slug:
            item = Plan.objects.filter(Q(owner__id=academy_id) | Q(owner=None),
                                       slug=plan_slug).exclude(status='DELETED').first()
            if not item:
                raise ValidationException('Plan not found', code=404, slug='not-found')

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
        plan = Plan.objects.filter(Q(owner__id=academy_id) | Q(owner=None),
                                   id=plan_id).exclude(status='DELETED').first()
        if not plan:
            raise ValidationException('Plan not found', code=404, slug='not-found')

        data = request.data
        if not 'owner' in data or data['owner'] is not None:
            data['owner'] = academy_id

        serializer = ServiceSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)

    @capable_of('crud_plan')
    def delete(self, request, plan_id=None, academy_id=None):
        plan = Plan.objects.filter(Q(owner__id=academy_id) | Q(owner=None),
                                   id=plan_id).exclude(status='DELETED').first()
        if not plan:
            raise ValidationException('Plan not found', code=404, slug='not-found')

        plan.status = 'DELETED'
        plan.save()

        return Response(status=status.HTTP_204_NO_CONTENT)


class ServiceView(APIView):
    permission_classes = [AllowAny]
    extensions = APIViewExtensions(sort='-created_at', paginate=True)

    def get(self, request, service_slug=None):
        handler = self.extensions(request)

        if service_slug:
            item = Service.objects.filter(slug=service_slug).first()

            if not item:
                raise ValidationException('Service not found', code=404, slug='not-found')

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
    permission_classes = [AllowAny]
    extensions = APIViewExtensions(sort='-created_at', paginate=True)

    @capable_of('read_service')
    def get(self, request, service_slug=None, academy_id=None):
        handler = self.extensions(request)

        if service_slug:
            item = Service.objects.filter(Q(owner__id=academy_id) | Q(owner=None) | Q(private=False),
                                          slug=service_slug).first()

            if not item:
                raise ValidationException('Service not found', code=404, slug='not-found')

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

        if not service:
            raise ValidationException('Service not found', code=404, slug='not-found')

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
    permission_classes = [AllowAny]
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
    permission_classes = [AllowAny]
    extensions = APIViewExtensions(sort='-created_at', paginate=True)

    def get(self, request, credit_id=None):
        handler = self.extensions(request)
        now = timezone.now()

        if credit_id:
            item = Credit.objects.filter(Q(valid_until__gte=now) | Q(valid_until=None),
                                         id=credit_id,
                                         invoice__user=request.user).first()

            if not item:
                raise ValidationException('Credit not found', code=404, slug='not-found')

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
    permission_classes = [AllowAny]
    extensions = APIViewExtensions(sort='-created_at', paginate=True)

    def get(self, request, subscription_id=None):
        handler = self.extensions(request)
        now = timezone.now()

        if subscription_id:
            item = Subscription.objects.filter(
                Q(valid_until__gte=now) | Q(valid_until=None), id=subscription_id, user=request.user).exclude(
                    status='CANCELLED').exclude(status='DEPRECATED').exclude(status='PAYMENT_ISSUE').first()

            if not item:
                raise ValidationException('Subscription not found', code=404, slug='not-found')

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


class AcademySubscriptionView(APIView):
    permission_classes = [AllowAny]
    extensions = APIViewExtensions(sort='-created_at', paginate=True)

    @capable_of('read_subscription')
    def get(self, request, subscription_id=None):
        handler = self.extensions(request)
        now = timezone.now()

        if subscription_id:
            item = Subscription.objects.filter(
                Q(valid_until__gte=now) | Q(valid_until=None), id=subscription_id).exclude(
                    status='CANCELLED').exclude(status='DEPRECATED').exclude(status='PAYMENT_ISSUE').first()

            if not item:
                raise ValidationException('Subscription not found', code=404, slug='not-found')

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
    permission_classes = [AllowAny]
    extensions = APIViewExtensions(sort='-created_at', paginate=True)

    def get(self, request, invoice_id=None):
        handler = self.extensions(request)
        now = timezone.now()

        if invoice_id:
            item = Invoice.objects.filter(id=invoice_id, user=request.user).first()

            if not item:
                raise ValidationException('Invoice not found', code=404, slug='not-found')

            serializer = GetInvoiceSerializer(items, many=True)
            return handler.response(serializer.data)

        items = Invoice.objects.filter(user=request.user)

        if status := request.GET.get('status'):
            items = items.filter(status__in=status.split(','))

        items = handler.queryset(items)
        serializer = GetInvoiceSmallSerializer(items, many=True)

        return handler.response(serializer.data)


class AcademyInvoiceView(APIView):
    permission_classes = [AllowAny]
    extensions = APIViewExtensions(sort='-created_at', paginate=True)

    @capable_of('read_invoice')
    def get(self, request, invoice_id=None, academy_id=None):
        handler = self.extensions(request)
        now = timezone.now()

        if invoice_id:
            item = Invoice.objects.filter(id=invoice_id, user=request.user, academy__id=academy_id).first()

            if not item:
                raise ValidationException('Invoice not found', code=404, slug='not-found')

            serializer = GetInvoiceSerializer(items, many=True)
            return handler.response(serializer.data)

        items = Invoice.objects.filter(user=request.user, academy__id=academy_id)

        if status := request.GET.get('status'):
            items = items.filter(status__in=status.split(','))

        items = handler.queryset(items)
        serializer = GetInvoiceSmallSerializer(items, many=True)

        return handler.response(serializer.data)
