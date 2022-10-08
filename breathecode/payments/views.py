from rest_framework.views import APIView
from breathecode.payments.models import Plan
from breathecode.payments.serializers import PlanSerializer
# from rest_framework.response import Response
from breathecode.utils import APIViewExtensions
from rest_framework.permissions import AllowAny

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

            serializer = PlanSerializer(item, many=False)
            return handler.response(serializer.data)

        if service_slug:
            items = Plan.objects.filter(services_slug=service_slug)

            serializer = PlanSerializer(items, many=True)
            return handler.response(serializer.data)

        items = Plan.objects.filter(slug=plan_slug)

        event = request.GET.get('event', None)
        if event is not None:
            filtered = True
            items = items.filter(event__in=event.split(','))

        items = handler.queryset(items)
        serializer = HookSerializer(items, many=True)

        return handler.response(serializer.data)
