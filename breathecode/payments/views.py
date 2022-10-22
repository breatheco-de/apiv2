from rest_framework.views import APIView
from breathecode.payments.models import Credit, Plan, Service
from breathecode.payments.serializers import (GetCreditSerializer, GetPlanSerializer, GetServiceSerializer,
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

        if service_slug:
            items = Plan.objects.filter(services_slug=service_slug)

            serializer = GetPlanSerializer(items, many=True)
            return handler.response(serializer.data)

        items = Plan.objects.filter(slug=plan_slug)

        items = handler.queryset(items)
        serializer = GetPlanSerializer(items, many=True)

        return handler.response(serializer.data)


class AcademyPlanView(APIView):
    permission_classes = [AllowAny]
    extensions = APIViewExtensions(sort='-created_at', paginate=True)

    @capable_of('read_plan')
    def get(self, request, plan_slug=None, service_slug=None, academy_id=None):
        handler = self.extensions(request)

        # owner
        if plan_slug:
            item = Plan.objects.filter(Q(owner__id=academy_id) | Q(owner=None),
                                       slug=plan_slug).exclude(status='DELETED').first()
            if not item:
                raise ValidationException('Plan not found', code=404, slug='not-found')

            serializer = GetPlanSerializer(item, many=False)
            return handler.response(serializer.data)

        if service_slug:
            items = Plan.objects.filter(Q(owner__id=academy_id) | Q(owner=None),
                                        services_slug=service_slug).exclude(status='DELETED')

            serializer = GetPlanSerializer(items, many=True)
            return handler.response(serializer.data)

        items = Plan.objects.filter(Q(owner__id=academy_id) | Q(owner=None),
                                    slug=plan_slug).exclude(status='DELETED')

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

    def get(self, request, invoice_id=None, service_slug=None):
        handler = self.extensions(request)

        if service_slug:
            items = Credit.objects.filter(services_slug=service_slug)

            serializer = GetPlanSerializer(items, many=True)
            return handler.response(serializer.data)

        items = Plan.objects.filter(slug=plan_slug)

        event = request.GET.get('event', None)
        if event is not None:
            filtered = True
            items = items.filter(event__in=event.split(','))

        items = handler.queryset(items)
        serializer = HookSerializer(items, many=True)

        return handler.response(serializer.data)


class CreditView(APIView):
    permission_classes = [AllowAny]
    extensions = APIViewExtensions(sort='-created_at', paginate=True)

    def get(self, request, invoice_id=None, service_slug=None):
        handler = self.extensions(request)
        now = timezone.now()

        if invoice_id:
            items = Credit.objects.filter(Q(valid_until__gte=now) | Q(valid_until=None),
                                          invoice__id=invoice_id,
                                          invoice__user=request.user)

            serializer = GetCreditSerializer(items, many=True)
            return handler.response(serializer.data)

        if service_slug:
            items = Credit.objects.filter(Q(valid_until__gte=now) | Q(valid_until=None),
                                          services_slug=service_slug,
                                          invoice__user=request.user)

            serializer = GetCreditSerializer(items, many=True)
            return handler.response(serializer.data)

        items = Credit.objects.filter(Q(valid_until__gte=now) | Q(valid_until=None),
                                      invoice__user=request.user)

        items = handler.queryset(items)
        serializer = GetCreditSerializer(items, many=True)

        return handler.response(serializer.data)
