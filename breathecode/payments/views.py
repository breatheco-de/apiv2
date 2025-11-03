from datetime import timedelta
from typing import Any

from adrf.views import APIView
from capyc.core.i18n import translation
from capyc.core.shorteners import C
from capyc.rest_framework.exceptions import PaymentException, ValidationException
from django.contrib.auth.models import User
from django.core.cache import cache
from django.db import transaction
from django.db.models import CharField, Count, F, Q, QuerySet, Value
from django.utils import timezone
from django_redis import get_redis_connection
from linked_services.rest_framework.decorators import scope
from linked_services.rest_framework.types import LinkedApp, LinkedHttpRequest, LinkedToken
from redis.exceptions import LockError
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

import breathecode.activity.tasks as tasks_activity
from breathecode.admissions.models import Academy, Cohort
from breathecode.authenticate.actions import get_academy_from_body, get_user_language
from breathecode.commission.tasks import register_referral_from_invoice
from breathecode.payments import actions, tasks
from breathecode.payments.actions import (
    PlanFinder,
    add_items_to_bag,
    apply_pricing_ratio,
    filter_consumables,
    filter_void_consumable_balance,
    get_amount,
    get_amount_by_chosen_period,
    get_available_coupons,
    get_balance_by_resource,
    get_discounted_price,
    max_coupons_allowed,
)
from breathecode.payments.caches import PlanFinancingCache, PlanOfferCache, SubscriptionCache
from breathecode.payments.models import (
    AcademyService,
    Bag,
    CohortSet,
    Consumable,
    ConsumptionSession,
    Coupon,
    Currency,
    EventTypeSet,
    FinancingOption,
    FinancialReputation,
    Invoice,
    MentorshipServiceSet,
    PaymentMethod,
    Plan,
    PlanFinancing,
    PlanOffer,
    PlanServiceItem,
    Seller,
    Service,
    ServiceItem,
    Subscription,
    SubscriptionBillingTeam,
    SubscriptionSeat,
)
from breathecode.payments.serializers import (
    BillingTeamAutoRechargeSerializer,
    CohortSetSerializer,
    FinancingOptionSerializer,
    GetAbstractIOweYouSmallSerializer,
    GetAcademyServiceSmallSerializer,
    GetBagSerializer,
    GetConsumptionSessionSerializer,
    GetCouponSerializer,
    GetCouponWithPlansSerializer,
    GetCohortSerializer,
    GetCohortSetSerializer,
    GetEventTypeSetSerializer,
    GetEventTypeSetSmallSerializer,
    GetFinancingOptionSerializer,
    GetInvoiceSerializer,
    GetInvoiceSmallSerializer,
    GetMentorshipServiceSetSerializer,
    GetMentorshipServiceSetSmallSerializer,
    GetPaymentMethod,
    GetPlanFinancingSerializer,
    GetPlanOfferSerializer,
    GetPlanSerializer,
    GetServiceItemWithFeaturesSerializer,
    GetServiceSerializer,
    GetSubscriptionSerializer,
    PaymentMethodSerializer,
    PlanSerializer,
    POSTAcademyServiceSerializer,
    PUTAcademyServiceSerializer,
    ServiceItemSerializer,
    ServiceSerializer,
)
from breathecode.payments.services.stripe import Stripe
from breathecode.payments.signals import reimburse_service_units
from breathecode.utils import APIViewExtensions, getLogger, validate_conversion_info
from breathecode.utils.decorators.capable_of import capable_of
from breathecode.utils.decorators.consume import discount_consumption_sessions
from breathecode.utils.redis import Lock

logger = getLogger(__name__)

IS_DJANGO_REDIS = hasattr(cache, "fake") is False


class PlanView(APIView):
    permission_classes = [AllowAny]
    extensions = APIViewExtensions(sort="-id", paginate=True)

    def get(self, request, plan_slug=None, service_slug=None):

        def is_onboarding(value: str):
            if filtering:
                return Q()

            return Q(is_onboarding=value.lower() == "true")

        handler = self.extensions(request)
        lang = get_user_language(request)
        country_code = request.GET.get("country_code")

        if plan_slug:
            item = Plan.objects.filter(slug=plan_slug).first()
            if not item:
                raise ValidationException(
                    translation(lang, en="Plan not found", es="Plan no existe", slug="not-found"), code=404
                )

            serializer = GetPlanSerializer(
                item,
                many=False,
                context={"academy_id": request.GET.get("academy"), "country_code": country_code},
                select=request.GET.get("select"),
            )
            return handler.response(serializer.data)

        filtering = "cohort" in request.GET or "syllabus" in request.GET
        query = handler.lookup.build(
            lang,
            strings={
                "exact": [
                    "service_items__service__slug",
                    "currency__code",
                ],
            },
            overwrite={
                "service_slug": "service_items__service__slug",
            },
            custom_fields={"is_onboarding": is_onboarding},
        )

        if filtering:
            items = PlanFinder(request, query=query).get_plans_belongs_from_request().exclude(status="DELETED")

        else:
            items = Plan.objects.filter(query).exclude(status="DELETED")

        items = handler.queryset(items)
        serializer = GetPlanSerializer(
            items,
            many=True,
            context={"academy_id": request.GET.get("academy"), "country_code": country_code},
            select=request.GET.get("select"),
        )

        return handler.response(serializer.data)


class AcademyPlanView(APIView):
    extensions = APIViewExtensions(sort="-id", paginate=True)

    @capable_of("read_subscription")
    def get(self, request, plan_id=None, plan_slug=None, service_slug=None, academy_id=None):

        def is_onboarding(value: str):
            if filtering:
                return Q()

            return Q(is_onboarding=value.lower() == "true")

        handler = self.extensions(request)
        lang = get_user_language(request)

        if plan_id or plan_slug:
            item = (
                Plan.objects.filter(
                    Q(id=plan_id) | Q(slug=plan_slug, slug__isnull=False), Q(owner__id=academy_id) | Q(owner=None)
                )
                .exclude(status="DELETED")
                .first()
            )
            if not item:
                raise ValidationException(
                    translation(lang, en="Plan not found", es="Plan no existe", slug="not-found"), code=404
                )

            serializer = GetPlanSerializer(
                item,
                many=False,
                context={"academy_id": academy_id, "country_code": request.GET.get("country_code")},
                select=request.GET.get("select"),
            )
            return handler.response(serializer.data)

        filtering = "cohort" in request.GET or "syllabus" in request.GET
        query = handler.lookup.build(
            lang,
            strings={
                "exact": [
                    "service_items__service__slug",
                    "currency__code",
                ],
            },
            overwrite={
                "service_slug": "service_items__service__slug",
            },
            custom_fields={"is_onboarding": is_onboarding},
        )

        if filtering:
            items = (
                PlanFinder(request, query=query)
                .get_plans_belongs_from_request()
                .filter(Q(owner__id=academy_id) | Q(owner=None))
                .exclude(status="DELETED")
            )

        else:
            items = Plan.objects.filter(query, Q(owner__id=academy_id) | Q(owner=None)).exclude(status="DELETED")

        # Add "like" search filter for slug or title
        if like := request.GET.get("like"):
            items = items.filter(Q(slug__icontains=like) | Q(title__icontains=like))

        items = handler.queryset(items)
        serializer = GetPlanSerializer(
            items,
            many=True,
            context={"academy_id": academy_id, "country_code": request.GET.get("country_code")},
            select=request.GET.get("select"),
        )

        return handler.response(serializer.data)

    @capable_of("crud_subscription")
    def post(self, request, academy_id=None):
        lang = get_user_language(request)

        data = {}

        for key in request.data:
            if key in ["owner", "owner_id", "currency"]:
                continue

            data[key] = request.data[key]

        data = request.data
        if not "owner" in data or data["owner"] is not None:
            data["owner"] = academy_id

        currency = data.get("currency", "")
        if currency and (currency := Currency.objects.filter(code=currency).first()):
            data["currency"] = currency.id

        else:
            raise ValidationException(
                translation(lang, en="Currency not found", es="Divisa no encontrada", slug="currency-not-found"),
                code=400,
            )

        serializer = PlanSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=201)

    @capable_of("crud_subscription")
    def put(self, request, plan_id=None, plan_slug=None, academy_id=None):
        lang = get_user_language(request)

        plan = (
            Plan.objects.filter(Q(id=plan_id) | Q(slug=plan_slug), Q(owner__id=academy_id) | Q(owner=None))
            .exclude(status="DELETED")
            .first()
        )
        if not plan:
            raise ValidationException(
                translation(lang, en="Plan not found", es="El plan no existe", slug="not-found"), code=404
            )

        data = {}

        if plan.currency:
            data["currency"] = plan.currency.id

        for key in request.data:
            if key in ["owner", "owner_id"]:
                continue

            data[key] = request.data[key]

        serializer = PlanSerializer(plan, data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of("crud_subscription")
    def delete(self, request, plan_id=None, plan_slug=None, academy_id=None):
        lang = get_user_language(request)

        plan = (
            Plan.objects.filter(Q(id=plan_id) | Q(slug=plan_slug), Q(owner__id=academy_id) | Q(owner=None), id=plan_id)
            .exclude(status="DELETED")
            .first()
        )
        if not plan:
            raise ValidationException(
                translation(lang, en="Plan not found", es="Plan no existe", slug="not-found"), code=404
            )

        plan.status = "DELETED"
        plan.save()

        return Response(status=status.HTTP_204_NO_CONTENT)


class AcademyFinancingOptionView(APIView):
    """Manage financing options for academy plans"""

    extensions = APIViewExtensions(sort="-id", paginate=True)

    @capable_of("read_subscription")
    def get(self, request, financing_option_id=None, academy_id=None):
        handler = self.extensions(request)
        lang = get_user_language(request)

        if financing_option_id:
            # Only return if owned by this academy OR is global (academy=None)
            item = FinancingOption.objects.filter(
                Q(academy__id=academy_id) | Q(academy=None), id=financing_option_id
            ).first()
            if not item:
                raise ValidationException(
                    translation(
                        lang,
                        en="Financing option not found or does not belong to this academy",
                        es="Opción de financiamiento no encontrada o no pertenece a esta academia",
                        slug="not-found",
                    ),
                    code=404,
                )

            serializer = GetFinancingOptionSerializer(
                item, many=False, context={"lang": lang, "country_code": request.GET.get("country_code")}
            )
            return Response(serializer.data)

        # List financing options for this academy and global ones
        items = FinancingOption.objects.filter(Q(academy__id=academy_id) | Q(academy=None))

        # Filter by currency if provided
        currency_code = request.GET.get("currency")
        if currency_code:
            items = items.filter(currency__code__iexact=currency_code)

        # Filter by months if provided
        how_many_months = request.GET.get("how_many_months")
        if how_many_months:
            items = items.filter(how_many_months=int(how_many_months))

        items = handler.queryset(items)
        serializer = GetFinancingOptionSerializer(
            items, many=True, context={"lang": lang, "country_code": request.GET.get("country_code")}
        )

        return handler.response(serializer.data)

    @capable_of("crud_subscription")
    def post(self, request, academy_id=None):
        lang = get_user_language(request)

        # Validate and convert currency code to ID
        data = request.data.copy()
        currency_code = data.get("currency", "")

        if currency_code:
            currency = Currency.objects.filter(code__iexact=currency_code).first()
            if not currency:
                raise ValidationException(
                    translation(lang, en="Currency not found", es="Divisa no encontrada", slug="currency-not-found"),
                    code=400,
                )
            data["currency"] = currency.id
        else:
            raise ValidationException(
                translation(lang, en="Currency is required", es="Divisa es requerida", slug="currency-required"),
                code=400,
            )

        serializer = FinancingOptionSerializer(data=data)
        serializer.is_valid(raise_exception=True)

        # Set academy ownership
        financing_option = serializer.save(academy_id=academy_id)

        # Return using GET serializer for consistent response
        response_serializer = GetFinancingOptionSerializer(financing_option, many=False, context={"lang": lang})

        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @capable_of("crud_subscription")
    def put(self, request, financing_option_id=None, academy_id=None):
        lang = get_user_language(request)

        # Only allow updating financing options owned by this academy (not global ones)
        financing_option = FinancingOption.objects.filter(academy__id=academy_id, id=financing_option_id).first()
        if not financing_option:
            raise ValidationException(
                translation(
                    lang,
                    en="Financing option not found or does not belong to this academy",
                    es="Opción de financiamiento no encontrada o no pertenece a esta academia",
                ),
                slug="not-found",
                code=404,
            )

        # Validate and convert currency code to ID if provided
        data = request.data.copy()
        if "currency" in data and isinstance(data["currency"], str):
            currency = Currency.objects.filter(code__iexact=data["currency"]).first()
            if not currency:
                raise ValidationException(
                    translation(lang, en="Currency not found", es="Divisa no encontrada", slug="currency-not-found"),
                    code=400,
                )
            data["currency"] = currency.id

        serializer = FinancingOptionSerializer(financing_option, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Return using GET serializer for consistent response
        response_serializer = GetFinancingOptionSerializer(serializer.instance, many=False, context={"lang": lang})

        return Response(response_serializer.data, status=status.HTTP_200_OK)

    @capable_of("crud_subscription")
    def delete(self, request, financing_option_id=None, academy_id=None):
        lang = get_user_language(request)

        # Only allow deleting financing options owned by this academy
        financing_option = FinancingOption.objects.filter(academy__id=academy_id, id=financing_option_id).first()
        if not financing_option:
            raise ValidationException(
                translation(
                    lang,
                    en="Financing option not found or does not belong to this academy",
                    es="Opción de financiamiento no encontrada o no pertenece a esta academia",
                ),
                slug="not-found",
                code=404,
            )

        # Check if financing option is being used by any plans
        plans_using = Plan.objects.filter(financing_options=financing_option).count()
        if plans_using > 0:
            raise ValidationException(
                translation(
                    lang,
                    en=f"Cannot delete financing option. It is being used by {plans_using} plan(s)",
                    es=f"No se puede eliminar la opción de financiamiento. Está siendo usada por {plans_using} plan(es)",
                ),
                slug="financing-option-in-use",
                code=400,
            )

        financing_option.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


class AcademyCohortSetView(APIView):
    """Manage CohortSets for an academy."""

    extensions = APIViewExtensions(sort="-id", paginate=True)

    @capable_of("read_plan")
    def get(self, request, cohort_set_id=None, cohort_set_slug=None, academy_id=None):
        """Get all cohort sets or a specific one."""
        handler = self.extensions(request)
        lang = get_user_language(request)

        if cohort_set_id or cohort_set_slug:
            # Get specific cohort set
            cohort_set = (
                CohortSet.objects.filter(
                    Q(id=cohort_set_id) | Q(slug=cohort_set_slug), academy__id=academy_id
                ).first()
            )
            if not cohort_set:
                raise ValidationException(
                    translation(lang, en="CohortSet not found", es="CohortSet no encontrado", slug="not-found"),
                    code=404,
                )

            serializer = GetCohortSetSerializer(cohort_set, many=False)
            return handler.response(serializer.data)

        # Get all cohort sets
        items = CohortSet.objects.filter(academy__id=academy_id)
        items = handler.queryset(items)
        serializer = GetCohortSetSerializer(items, many=True)

        return handler.response(serializer.data)

    @capable_of("crud_plan")
    def post(self, request, academy_id=None):
        """Create a new CohortSet."""
        lang = get_user_language(request)

        data = request.data.copy()
        data["academy"] = academy_id

        serializer = CohortSetSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            # Fetch the created cohort set with relationships
            cohort_set = CohortSet.objects.get(id=serializer.data["id"])
            return Response(GetCohortSetSerializer(cohort_set, many=False).data, status=201)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of("crud_plan")
    def put(self, request, cohort_set_id=None, cohort_set_slug=None, academy_id=None):
        """Update a CohortSet."""
        lang = get_user_language(request)

        cohort_set = (
            CohortSet.objects.filter(Q(id=cohort_set_id) | Q(slug=cohort_set_slug), academy__id=academy_id).first()
        )
        if not cohort_set:
            raise ValidationException(
                translation(lang, en="CohortSet not found", es="CohortSet no encontrado", slug="not-found"), code=404
            )

        serializer = CohortSetSerializer(cohort_set, data=request.data)
        if serializer.is_valid():
            serializer.save()
            # Fetch the updated cohort set with relationships
            cohort_set = CohortSet.objects.get(id=cohort_set.id)
            return Response(GetCohortSetSerializer(cohort_set, many=False).data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of("crud_plan")
    def delete(self, request, cohort_set_id=None, cohort_set_slug=None, academy_id=None):
        """Delete a CohortSet."""
        lang = get_user_language(request)

        cohort_set = (
            CohortSet.objects.filter(Q(id=cohort_set_id) | Q(slug=cohort_set_slug), academy__id=academy_id).first()
        )
        if not cohort_set:
            raise ValidationException(
                translation(lang, en="CohortSet not found", es="CohortSet no encontrado", slug="not-found"), code=404
            )

        cohort_set.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


class AcademyCohortSetCohortView(APIView):
    """Manage cohorts in a CohortSet."""

    extensions = APIViewExtensions(sort="-id", paginate=True)

    @capable_of("read_plan")
    def get(self, request, cohort_set_id=None, cohort_set_slug=None, academy_id=None):
        """Get all cohorts in a CohortSet."""
        handler = self.extensions(request)
        lang = get_user_language(request)

        cohort_set = (
            CohortSet.objects.filter(Q(id=cohort_set_id) | Q(slug=cohort_set_slug), academy__id=academy_id).first()
        )
        if not cohort_set:
            raise ValidationException(
                translation(lang, en="CohortSet not found", es="CohortSet no encontrado", slug="not-found"), code=404
            )

        cohorts = cohort_set.cohorts.all()
        cohorts = handler.queryset(cohorts)
        serializer = GetCohortSerializer(cohorts, many=True)

        return handler.response(serializer.data)

    @capable_of("crud_plan")
    def put(self, request, cohort_set_id=None, cohort_set_slug=None, academy_id=None):
        """Add cohorts to a CohortSet."""
        lang = get_user_language(request)

        handler = self.extensions(request)
        query = handler.lookup.build(
            lang,
            ints={
                "in": [
                    "id",
                ],
            },
            strings={
                "in": [
                    "slug",
                ],
            },
            fix={"lower": "slug"},
        )

        errors = []
        cohort_set = (
            CohortSet.objects.filter(Q(id=cohort_set_id) | Q(slug=cohort_set_slug), academy__id=academy_id).first()
        )
        if not cohort_set:
            errors.append(C(translation(lang, en="CohortSet not found", es="CohortSet no encontrado", slug="not-found")))

        if not (items := Cohort.objects.filter(query)):
            errors.append(
                C(translation(lang, en="Cohort not found", es="Cohort no encontrada", slug="cohort-not-found"))
            )

        if errors:
            raise ValidationException(errors, code=404)

        to_add = set()
        for item in items:
            if item not in cohort_set.cohorts.all():
                to_add.add(item)

        if to_add:
            cohort_set.cohorts.add(*to_add)

        return Response({"status": "ok"}, status=status.HTTP_201_CREATED if to_add else status.HTTP_200_OK)

    @capable_of("crud_plan")
    def delete(self, request, cohort_set_id=None, cohort_set_slug=None, academy_id=None):
        """Remove cohorts from a CohortSet."""
        lang = get_user_language(request)

        handler = self.extensions(request)
        query = handler.lookup.build(
            lang,
            ints={
                "in": [
                    "id",
                ],
            },
            strings={
                "in": [
                    "slug",
                ],
            },
            fix={"lower": "slug"},
        )

        errors = []
        cohort_set = (
            CohortSet.objects.filter(Q(id=cohort_set_id) | Q(slug=cohort_set_slug), academy__id=academy_id).first()
        )
        if not cohort_set:
            errors.append(C(translation(lang, en="CohortSet not found", es="CohortSet no encontrado", slug="not-found")))

        if not (items := Cohort.objects.filter(query)):
            errors.append(
                C(translation(lang, en="Cohort not found", es="Cohort no encontrada", slug="cohort-not-found"))
            )

        if errors:
            raise ValidationException(errors, code=404)

        cohort_set.cohorts.remove(*items)

        return Response({"status": "ok"})


class ServiceView(APIView):
    permission_classes = [AllowAny]
    extensions = APIViewExtensions(sort="-id", paginate=True)

    def get(self, request, service_slug=None):
        handler = self.extensions(request)

        lang = get_user_language(request)

        # Check if user has read_service capability to view private services
        can_view_private = False
        if request.user and request.user.is_authenticated:
            academy_id = request.GET.get("academy")
            if academy_id and str(academy_id).isdigit():
                from breathecode.authenticate.models import ProfileAcademy

                capable = ProfileAcademy.objects.filter(
                    user=request.user.id, academy__id=int(academy_id), role__capabilities__slug="read_service"
                )
                can_view_private = capable.exists()

        if service_slug:
            # Filter by private status if user doesn't have capability
            if can_view_private:
                item = Service.objects.filter(slug=service_slug).first()
            else:
                item = Service.objects.filter(slug=service_slug, private=False).first()

            if not item:
                raise ValidationException(
                    translation(lang, en="Service not found", es="No existe el Servicio", slug="not-found"), code=404
                )

            serializer = GetServiceSerializer(
                item, many=False, context={"academy_id": request.GET.get("academy")}, select=request.GET.get("select")
            )
            return handler.response(serializer.data)

        # Filter services based on capability
        if can_view_private:
            items = Service.objects.filter()
        else:
            items = Service.objects.filter(private=False)

        # Add optional academy owner filter
        if academy_id := request.GET.get("academy"):
            if str(academy_id).isdigit():
                items = items.filter(Q(owner__id=int(academy_id)) | Q(owner=None))

        if group := request.GET.get("group"):
            items = items.filter(groups__name=group)

        if cohort_slug := request.GET.get("cohort_slug"):
            items = items.filter(cohorts__slug=cohort_slug)

        if mentorship_service_slug := request.GET.get("mentorship_service_slug"):
            items = items.filter(mentorship_services__slug=mentorship_service_slug)

        # Add "like" search filter for slug or title
        if like := request.GET.get("like"):
            items = items.filter(Q(slug__icontains=like) | Q(title__icontains=like))

        items = handler.queryset(items)
        serializer = GetServiceSerializer(
            items, many=True, context={"academy_id": request.GET.get("academy")}, select=request.GET.get("select")
        )

        return handler.response(serializer.data)


class AcademyServiceView(APIView):
    extensions = APIViewExtensions(sort="-id", paginate=True)

    @capable_of("read_service")
    def get(self, request, service_slug=None, academy_id=None):
        handler = self.extensions(request)
        lang = get_user_language(request)

        if service_slug:
            item = Service.objects.filter(
                Q(owner__id=academy_id) | Q(owner=None) | Q(private=False), slug=service_slug
            ).first()

            if not item:
                raise ValidationException(
                    translation(lang, en="Service not found", es="No existe el Servicio", slug="not-found"), code=404
                )

            serializer = GetServiceSerializer(
                item, many=False, context={"academy_id": academy_id}, select=request.GET.get("select")
            )
            return handler.response(serializer.data)

        items = Service.objects.filter(Q(owner__id=academy_id) | Q(owner=None) | Q(private=False))

        if group := request.GET.get("group"):
            items = items.filter(groups__name=group)

        if cohort_slug := request.GET.get("cohort_slug"):
            items = items.filter(cohorts__slug=cohort_slug)

        if mentorship_service_slug := request.GET.get("mentorship_service_slug"):
            items = items.filter(mentorship_services__slug=mentorship_service_slug)

        # Add "like" search filter for slug or title
        if like := request.GET.get("like"):
            items = items.filter(Q(slug__icontains=like) | Q(title__icontains=like))

        items = handler.queryset(items)
        serializer = GetServiceSerializer(
            items, many=True, context={"academy_id": academy_id}, select=request.GET.get("select")
        )

        return handler.response(serializer.data)

    @capable_of("crud_service")
    def post(self, request, academy_id=None):
        data = request.data
        if not "owner" in data or data["owner"] is not None:
            data["owner"] = academy_id

        serializer = ServiceSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of("crud_service")
    def put(self, request, service_slug=None, academy_id=None):
        service = Service.objects.filter(Q(owner__id=academy_id) | Q(owner=None), slug=service_slug).first()
        lang = get_user_language(request)

        if not service:
            raise ValidationException(
                translation(lang, en="Service not found", es="No existe el Servicio", slug="not-found"), code=404
            )

        data = request.data
        if not "owner" in data or data["owner"] is not None:
            data["owner"] = academy_id

        serializer = ServiceSerializer(service, data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AcademyAcademyServiceView(APIView):
    extensions = APIViewExtensions(sort="-id", paginate=True)

    @capable_of("read_academyservice")
    def get(self, request, academy_id=None, service_slug=None):
        handler = self.extensions(request)
        lang = get_user_language(request)
        country_code = request.GET.get("country_code")
        query = handler.lookup.build(
            lang,
            strings={
                "exact": [
                    "currency__code",
                ],
            },
        )

        if service_slug is not None:
            item = AcademyService.objects.filter(query, academy__id=academy_id, service__slug=service_slug).first()
            if item is None:
                raise ValidationException(
                    translation(
                        lang,
                        en="There is no Academy Service with that service slug for the specified currency",
                        es="No existe ningún Academy Service con ese slug de Service para la moneda especificada",
                        slug="academy-service-not-found-for-currency",
                    ),
                    code=404,
                )

            serializer = GetAcademyServiceSmallSerializer(item, context={"country_code": country_code})
            return handler.response(serializer.data)

        items = AcademyService.objects.filter(query, academy__id=academy_id)

        if mentorship_service_set := request.GET.get("mentorship_service_set"):
            items = items.filter(available_mentorship_service_sets__slug__exact=mentorship_service_set)

        if event_type_set := request.GET.get("event_type_set"):
            items = items.filter(available_event_type_sets__slug__exact=event_type_set)

        # Add "like" search filter for service slug or title
        if like := request.GET.get("like"):
            items = items.filter(Q(service__slug__icontains=like) | Q(service__title__icontains=like))

        items = handler.queryset(items)
        serializer = GetAcademyServiceSmallSerializer(items, many=True, context={"country_code": country_code})

        return handler.response(serializer.data)

    @capable_of("crud_academyservice")
    def post(self, request, academy_id=None):
        lang = get_user_language(request)
        data = request.data.copy()

        data["academy"] = academy_id

        # Convert currency code to ID
        currency_code = data.get("currency", "")
        if currency_code:
            currency = Currency.objects.filter(code__iexact=currency_code).first()
            if not currency:
                raise ValidationException(
                    translation(lang, en="Currency not found", es="Divisa no encontrada", slug="currency-not-found"),
                    code=400,
                )
            data["currency"] = currency.id
        else:
            raise ValidationException(
                translation(lang, en="Currency is required", es="Divisa es requerida", slug="currency-required"),
                code=400,
            )

        serializer = POSTAcademyServiceSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of("crud_academyservice")
    def put(self, request, service_slug=None, academy_id=None):
        service = Service.objects.filter(Q(owner__id=academy_id) | Q(owner=None), slug=service_slug).first()
        lang = get_user_language(request)

        if not service:
            raise ValidationException(
                translation(lang, en="Service not found", es="No existe el Servicio", slug="service-not-found"),
                code=404,
            )

        academyservice = AcademyService.objects.filter(service=service.id, academy__id=academy_id).first()

        if not academyservice:
            raise ValidationException(
                translation(
                    lang,
                    en="Academy Service not found",
                    es="No existe el Academy Service",
                    slug="academyservice-not-found",
                ),
                code=404,
            )

        serializer = PUTAcademyServiceSerializer(academyservice, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ServiceItemView(APIView):
    permission_classes = [AllowAny]
    extensions = APIViewExtensions(sort="-id", paginate=True)

    def get(self, request, service_slug=None):
        handler = self.extensions(request)
        lang = get_user_language(request)

        items = ServiceItem.objects.none()

        if plan := request.GET.get("plan"):
            args = {"id": int(plan)} if plan.isnumeric() else {"slug": plan}

            p = Plan.objects.filter(**args).first()
            if not p:
                raise ValidationException(
                    translation(lang, en="Plan not found", es="No existe el Plan", slug="not-found"), code=404
                )

            items |= p.service_items.all()
            items = items.distinct()

        else:
            items = ServiceItem.objects.filter()

        if service_slug:
            items = items.filter(service__slug=service_slug)

        if unit_type := request.GET.get("unit_type"):
            items = items.filter(unit_type__in=unit_type.split(","))

        items = items.annotate(lang=Value(lang, output_field=CharField()))

        items = handler.queryset(items)
        serializer = GetServiceItemWithFeaturesSerializer(items, many=True)

        return handler.response(serializer.data)


class AcademyServiceItemView(APIView):
    """
    Academy endpoint to manage ServiceItems.
    GET: List and filter service items
    POST: Create new service items (immutable after creation)
    """

    extensions = APIViewExtensions(sort="-id", paginate=True)

    @capable_of("read_service")
    def get(self, request, academy_id=None):
        """
        List and filter ServiceItems for an academy.

        Query Parameters:
        - service: Filter by service ID or slug
        - is_renewable: Filter by renewable status (true/false)
        - is_team_allowed: Filter by team allowed status (true/false)
        - renew_at: Filter by renewal period number
        - renew_at_unit: Filter by renewal unit (DAY/WEEK/MONTH/YEAR)
        - how_many: Filter by quantity (use -1 for unlimited)
        - unit_type: Filter by unit type (UNIT/CREDIT/other)
        - how_many_gt: Filter items with how_many greater than value
        - how_many_lt: Filter items with how_many less than value
        """
        handler = self.extensions(request)
        lang = get_user_language(request)

        # Start with service items from services owned by the academy or global services
        items = ServiceItem.objects.filter(Q(service__owner__id=academy_id) | Q(service__owner=None))

        # Filter by service (ID or slug)
        if service := request.GET.get("service"):
            if service.isdigit():
                items = items.filter(service__id=int(service))
            else:
                items = items.filter(service__slug=service)

        # Filter by boolean fields
        if is_renewable := request.GET.get("is_renewable"):
            items = items.filter(is_renewable=is_renewable.lower() == "true")

        if is_team_allowed := request.GET.get("is_team_allowed"):
            items = items.filter(is_team_allowed=is_team_allowed.lower() == "true")

        # Filter by renewal parameters
        if renew_at := request.GET.get("renew_at"):
            if renew_at.isdigit():
                items = items.filter(renew_at=int(renew_at))

        if renew_at_unit := request.GET.get("renew_at_unit"):
            items = items.filter(renew_at_unit=renew_at_unit.upper())

        # Filter by how_many (quantity)
        if how_many := request.GET.get("how_many"):
            if how_many.lstrip("-").isdigit():
                items = items.filter(how_many=int(how_many))

        # Range filters for how_many
        if how_many_gt := request.GET.get("how_many_gt"):
            if how_many_gt.lstrip("-").isdigit():
                items = items.filter(how_many__gt=int(how_many_gt))

        if how_many_lt := request.GET.get("how_many_lt"):
            if how_many_lt.lstrip("-").isdigit():
                items = items.filter(how_many__lt=int(how_many_lt))

        # Filter by unit_type
        if unit_type := request.GET.get("unit_type"):
            items = items.filter(unit_type__in=unit_type.upper().split(","))

        # Add language annotation for serializer
        items = items.annotate(lang=Value(lang, output_field=CharField()))

        items = handler.queryset(items)
        serializer = GetServiceItemWithFeaturesSerializer(items, many=True)

        return handler.response(serializer.data)

    @capable_of("crud_service")
    def post(self, request, academy_id=None):
        """
        Create a new ServiceItem.

        Required fields:
        - service: Service ID
        - how_many: Number of units (-1 for unlimited, must be > 0)

        Optional fields:
        - unit_type: Default "UNIT"
        - sort_priority: Default 1
        - is_renewable: Default False
        - is_team_allowed: Default False (auto-set to True for SEAT type services)
        - renew_at: Default 1 (relevant only if is_renewable=True)
        - renew_at_unit: Default "MONTH" (relevant only if is_renewable=True)
        """
        lang = get_user_language(request)

        # Validate service exists
        service_id = request.data.get("service")
        if not service_id:
            raise ValidationException(
                translation(lang, en="service is required", es="service es requerido", slug="service-required"),
                code=400,
            )

        service = Service.objects.filter(id=service_id).first()
        if not service:
            raise ValidationException(
                translation(
                    lang,
                    en=f"Service with id {service_id} not found",
                    es=f"No se encontró el servicio con id {service_id}",
                    slug="service-not-found",
                ),
                code=404,
            )

        # Create ServiceItem
        serializer = ServiceItemSerializer(data=request.data)
        if serializer.is_valid():
            service_item = serializer.save()

            # Return with features if available
            service_item.lang = lang
            response_serializer = GetServiceItemWithFeaturesSerializer(service_item)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MeConsumableView(APIView):

    def get(self, request):
        items = Consumable.list(user=request.user)

        mentorship_services = MentorshipServiceSet.objects.none()
        mentorship_services = filter_consumables(request, items, mentorship_services, "mentorship_service_set")

        cohorts = CohortSet.objects.none()
        cohorts = filter_consumables(request, items, cohorts, "cohort_set")

        event_types = EventTypeSet.objects.none()
        event_types = filter_consumables(request, items, event_types, "event_type_set")

        balance = {
            "mentorship_service_sets": get_balance_by_resource(mentorship_services, "mentorship_service_set"),
            "cohort_sets": get_balance_by_resource(cohorts, "cohort_set"),
            "event_type_sets": get_balance_by_resource(event_types, "event_type_set"),
            "voids": filter_void_consumable_balance(request, items),
        }

        if request.GET.get("virtual") in ["true", "1", "y"]:
            actions.set_virtual_balance(balance, request.user)

        return Response(balance)


class AppConsumableView(MeConsumableView):
    permission_classes = [AllowAny]

    # created for mocking purposes
    def get_user(self, request: LinkedHttpRequest):
        return request.get_user()

    @scope(["read:consumable"])
    def get(self, request: LinkedHttpRequest, app: LinkedApp, token: LinkedToken):
        request.user = self.get_user(request)
        if request.user is None or request.user.is_anonymous:
            raise ValidationException("User not provided", code=400)

        return super().get(request)


class AcademyConsumableView(APIView):
    """
    Academy endpoint to view consumables for users in the academy.
    Filters by academy_id (from request header) and allows filtering by users and service slugs.
    """

    @capable_of("read_consumable")
    def get(self, request, academy_id=None):
        lang = get_user_language(request)
        utc_now = timezone.now()

        # Start with consumables that belong to the academy through subscriptions or plan_financings
        items = Consumable.objects.filter(
            Q(valid_until__gte=utc_now) | Q(valid_until=None),
            Q(subscription__academy_id=academy_id) | Q(plan_financing__academy_id=academy_id),
        ).exclude(how_many=0)

        # Filter by users if provided (comma-separated list of user IDs)
        if users := request.GET.get("users"):
            try:
                user_ids = [int(x.strip()) for x in users.split(",") if x.strip()]
                items = items.filter(user_id__in=user_ids)
            except ValueError:
                raise ValidationException(
                    translation(
                        lang,
                        en="users parameter must contain comma-separated integers",
                        es="El parámetro users debe contener enteros separados por comas",
                        slug="invalid-users-param",
                    ),
                    code=400,
                )

        # Filter by service slugs if provided (comma-separated list)
        if service_slugs := request.GET.get("service"):
            slugs = [s.strip() for s in service_slugs.split(",") if s.strip()]
            items = items.filter(service_item__service__slug__in=slugs)

        # Group by resource types
        mentorship_services = MentorshipServiceSet.objects.none()
        mentorship_services = filter_consumables(request, items, mentorship_services, "mentorship_service_set")

        cohorts = CohortSet.objects.none()
        cohorts = filter_consumables(request, items, cohorts, "cohort_set")

        event_types = EventTypeSet.objects.none()
        event_types = filter_consumables(request, items, event_types, "event_type_set")

        balance = {
            "mentorship_service_sets": get_balance_by_resource(mentorship_services, "mentorship_service_set"),
            "cohort_sets": get_balance_by_resource(cohorts, "cohort_set"),
            "event_type_sets": get_balance_by_resource(event_types, "event_type_set"),
            "voids": filter_void_consumable_balance(request, items),
        }

        return Response(balance)


class MentorshipServiceSetView(APIView):
    permission_classes = [AllowAny]
    extensions = APIViewExtensions(sort="-id", paginate=True)

    def get(self, request, mentorship_service_set_id=None):
        handler = self.extensions(request)

        lang = get_user_language(request)

        if mentorship_service_set_id:
            item = MentorshipServiceSet.objects.filter(id=mentorship_service_set_id).first()
            if not item:
                raise ValidationException(
                    translation(
                        lang,
                        en="Mentorship Service Set not found",
                        es="No existe el Servicio de Mentoría",
                        slug="not-found",
                    ),
                    code=404,
                )

            serializer = GetMentorshipServiceSetSerializer(item, many=False)

            return handler.response(serializer.data)

        query = handler.lookup.build(
            lang,
            slugs=[
                "",
                "academy",
                "mentorship_services",
            ],
            overwrite={
                "mentorship_service": "mentorship_services",
            },
        )

        items = MentorshipServiceSet.objects.filter(query)

        items = handler.queryset(items)
        serializer = GetMentorshipServiceSetSmallSerializer(items, many=True)

        return handler.response(serializer.data)


class EventTypeSetView(APIView):
    permission_classes = [AllowAny]
    extensions = APIViewExtensions(sort="-id", paginate=True)

    def get(self, request, event_type_set_id=None):
        handler = self.extensions(request)

        lang = get_user_language(request)

        if event_type_set_id:
            item = EventTypeSet.objects.filter(id=event_type_set_id).first()
            if not item:
                raise ValidationException(
                    translation(
                        lang, en="Event type set not found", es="No existe el tipo de evento", slug="not-found"
                    ),
                    code=404,
                )
            serializer = GetEventTypeSetSerializer(item, many=False)

            return handler.response(serializer.data)

        query = handler.lookup.build(
            lang,
            strings={"exact": ["event_types__lang"]},
            slugs=[
                "",
                "academy",
                "event_types",
            ],
            overwrite={
                "event_type": "event_types",
                "lang": "event_types__lang",
            },
        )

        items = EventTypeSet.objects.filter(query)

        items = handler.queryset(items)
        serializer = GetEventTypeSetSmallSerializer(items, many=True)

        return Response(serializer.data)


# TODO: this view is not cachable yet.
class MeSubscriptionView(APIView):
    # this cannot support cache because the cache does not support associated two models to a response yet
    extensions = APIViewExtensions(sort="-id")

    def get_lookup(self, key, value):
        args = ()
        kwargs = {}
        slug_key = f"{key}__slug__in"
        pk_key = f"{key}__id__in"

        for v in value.split(","):
            if slug_key not in kwargs and not v.isnumeric():
                kwargs[slug_key] = []

            if pk_key not in kwargs and v.isnumeric():
                kwargs[pk_key] = []

            if v.isnumeric():
                kwargs[pk_key].append(int(v))

            else:
                kwargs[slug_key].append(v)

        if len(kwargs) > 1:
            args = (Q(**{slug_key: kwargs[slug_key]}) | Q(**{pk_key: kwargs[pk_key]}),)
            kwargs = {}

        return args, kwargs

    def get(self, request):
        handler = self.extensions(request)

        now = timezone.now()

        subscriptions = Subscription.objects.filter(user=request.user)

        # NOTE: this is before feature/add-plan-duration branch, this will be outdated
        plan_financings = PlanFinancing.objects.filter(user=request.user)

        if subscription := request.GET.get("subscription"):
            subscriptions = subscriptions.filter(id=int(subscription))

        if plan_financing := request.GET.get("plan-financing"):
            plan_financings = plan_financings.filter(id=int(plan_financing))

        if subscription and not plan_financing:
            plan_financings = PlanFinancing.objects.none()

        if not subscription and plan_financing:
            subscriptions = Subscription.objects.none()

        if status := request.GET.get("status"):
            subscriptions = subscriptions.filter(status__in=status.split(","))
            plan_financings = plan_financings.filter(status__in=status.split(","))
        else:
            subscriptions = (
                subscriptions.exclude(status="DEPRECATED")
                .exclude(status="PAYMENT_ISSUE")
                .exclude(status="ERROR")
                .exclude(status="EXPIRED")
                .exclude(Q(status="CANCELLED") & (Q(next_payment_at__lt=now) | Q(valid_until__lt=now)))
            )
            plan_financings = (
                plan_financings.exclude(status="DEPRECATED")
                .exclude(status="PAYMENT_ISSUE")
                .exclude(status="ERROR")
                .exclude(status="EXPIRED")
                .exclude(Q(status="CANCELLED") & (Q(next_payment_at__lt=now) | Q(valid_until__lt=now)))
            )

        if invoice := request.GET.get("invoice"):
            ids = [int(x) for x in invoice if x.isnumeric()]
            subscriptions = subscriptions.filter(invoices__id__in=ids)
            plan_financings = plan_financings.filter(invoices__id__in=ids)

        # Filter by academy (accepts id(s) or slug(s))
        if academy := request.GET.get("academy"):
            args, kwargs = self.get_lookup("academy", academy)
            subscriptions = subscriptions.filter(*args, **kwargs)
            plan_financings = plan_financings.filter(*args, **kwargs)

        if service := request.GET.get("service"):
            service_items_args, service_items_kwargs = self.get_lookup("service_items__service", service)
            plans_args, plans_kwargs = self.get_lookup("plans__service_items__service", service)

            if service_items_args:
                subscriptions = subscriptions.filter(Q(*service_items_args) | Q(*plans_args))
                plan_financings = plan_financings.filter(*plans_args)

            else:
                subscriptions = subscriptions.filter(Q(**plans_kwargs) | Q(**service_items_kwargs))
                plan_financings = plan_financings.filter(**plans_kwargs)

        if plan := request.GET.get("plan"):
            args, kwargs = self.get_lookup("plans", plan)
            subscriptions = subscriptions.filter(*args, **kwargs)
            plan_financings = plan_financings.filter(*args, **kwargs)

        if selected_cohort_set := (request.GET.get("cohort-set-selected") or request.GET.get("cohort-set-selected")):
            args, kwargs = self.get_lookup("selected_cohort_set", selected_cohort_set)
            subscriptions = subscriptions.filter(*args, **kwargs)
            plan_financings = plan_financings.filter(*args, **kwargs)

        if selected_mentorship_service_set := (
            request.GET.get("mentorship-service-set-selected") or request.GET.get("selected-mentorship-service-set")
        ):
            args, kwargs = self.get_lookup("selected_mentorship_service_set", selected_mentorship_service_set)
            subscriptions = subscriptions.filter(*args, **kwargs)
            plan_financings = plan_financings.filter(*args, **kwargs)

        if selected_event_type_set := (
            request.GET.get("event-type-set-selected") or request.GET.get("selected-event-type-set")
        ):
            args, kwargs = self.get_lookup("selected_event_type_set", selected_event_type_set)
            subscriptions = subscriptions.filter(*args, **kwargs)
            plan_financings = plan_financings.filter(*args, **kwargs)

        only_valid = request.GET.get("only_valid")
        if only_valid == True or only_valid == "true":
            subscriptions = subscriptions.filter(Q(valid_until__gte=now) | Q(valid_until=None))
            plan_financings = plan_financings.filter(valid_until__gte=now)

        subscriptions = handler.queryset(subscriptions.distinct())
        subscription_serializer = GetSubscriptionSerializer(subscriptions, many=True)

        plan_financings = handler.queryset(plan_financings.distinct())
        plan_financing_serializer = GetPlanFinancingSerializer(plan_financings, many=True)

        return handler.response(
            {
                "subscriptions": subscription_serializer.data,
                "plan_financings": plan_financing_serializer.data,
            }
        )


class MeSubscriptionChargeView(APIView):
    extensions = APIViewExtensions(sort="-id", paginate=True)

    def put(self, request, subscription_id):
        utc_now = timezone.now()

        if not (subscription := Subscription.objects.filter(id=subscription_id, user=request.user).first()):
            raise ValidationException(
                translation(
                    request.user.language, en="Subscription not found", es="No existe la suscripción", slug="not-found"
                ),
                code=404,
            )

        if subscription.status != "PAYMENT_ISSUE" and subscription.status == "ERROR":
            raise ValidationException(
                translation(
                    request.user.language,
                    en="Nothing to charge too",
                    es="No hay nada que cobrar",
                    slug="nothing-to-charge",
                ),
                code=400,
            )

        if subscription.next_payment_at - timedelta(days=1) > utc_now:
            raise ValidationException(
                translation(
                    request.user.language,
                    en="The subscription time is not over",
                    es="El tiempo de la suscripción no ha terminado",
                    slug="time-not-over",
                ),
                code=400,
            )

        tasks.charge_subscription.delay(subscription_id)

        return Response({"status": "loading"}, status=status.HTTP_202_ACCEPTED)


class MeSubscriptionCancelView(APIView):
    extensions = APIViewExtensions(sort="-id", paginate=True)

    def put(self, request, subscription_id):
        lang = get_user_language(request)

        if not (subscription := Subscription.objects.filter(id=subscription_id, user=request.user).first()):
            raise ValidationException(
                translation(lang, en="Subscription not found", es="No existe la suscripción", slug="not-found"),
                code=404,
            )

        if subscription.status == "CANCELLED":
            raise ValidationException(
                translation(
                    lang,
                    en="Subscription already cancelled",
                    es="La suscripción ya está cancelada",
                    slug="already-cancelled",
                ),
                code=400,
            )

        if subscription.status == "DEPRECATED":
            raise ValidationException(
                translation(
                    lang,
                    en="This subscription is deprecated, so is already cancelled",
                    es="Esta suscripción está obsoleta, por lo que ya está cancelada",
                    slug="deprecated",
                ),
                code=400,
            )

        subscription.status = "CANCELLED"
        subscription.save()

        serializer = GetSubscriptionSerializer(subscription)

        return Response(serializer.data, status=status.HTTP_200_OK)


class MeSubscriptionReactivateView(APIView):
    extensions = APIViewExtensions(sort="-id", paginate=True)

    def put(self, request, subscription_id):
        lang = get_user_language(request)
        utc_now = timezone.now()

        if not (subscription := Subscription.objects.filter(id=subscription_id, user=request.user).first()):
            raise ValidationException(
                translation(lang, en="Subscription not found", es="No existe la suscripción", slug="not-found"),
                code=404,
            )

        if subscription.status == "ACTIVE":
            raise ValidationException(
                translation(
                    lang,
                    en="Subscription already active",
                    es="La suscripción ya está activa",
                    slug="already-active",
                ),
                code=400,
            )

        # Check if subscription can still be reactivated based on dates
        if subscription.next_payment_at and subscription.next_payment_at < utc_now:
            raise ValidationException(
                translation(
                    lang,
                    en=f"The reactivation period was until {subscription.next_payment_at.strftime('%Y-%m-%d %H:%M:%S')}, then user should buy a new subscription",
                    es=f"El período de reactivación fue hasta {subscription.next_payment_at.strftime('%Y-%m-%d %H:%M:%S')}, entonces el usuario debe comprar una nueva suscripción",
                    slug="reactivation-period-expired",
                ),
                code=400,
            )

        if subscription.valid_until and subscription.valid_until < utc_now:
            raise ValidationException(
                translation(
                    lang,
                    en=f"The reactivation period was until {subscription.valid_until.strftime('%Y-%m-%d %H:%M:%S')}, then user should buy a new subscription",
                    es=f"El período de reactivación fue hasta {subscription.valid_until.strftime('%Y-%m-%d %H:%M:%S')}, entonces el usuario debe comprar una nueva suscripción",
                    slug="reactivation-period-expired",
                ),
                code=400,
            )

        subscription.status = "ACTIVE"
        subscription.save()

        serializer = GetSubscriptionSerializer(subscription)

        return Response(serializer.data, status=status.HTTP_200_OK)


class MePlanFinancingChargeView(APIView):
    extensions = APIViewExtensions(sort="-id", paginate=True)

    def put(self, request, plan_financing_id):
        utc_now = timezone.now()

        if not (subscription := PlanFinancing.objects.filter(id=plan_financing_id, user=request.user).first()):
            raise ValidationException(
                translation(
                    request.user.language, en="Subscription not found", es="No existe la suscripción", slug="not-found"
                ),
                code=404,
            )

        if subscription.status != "PAYMENT_ISSUE" and subscription.status == "ERROR":
            raise ValidationException(
                translation(
                    request.user.language,
                    en="Nothing to charge too",
                    es="No hay nada que cobrar",
                    slug="nothing-to-charge",
                ),
                code=400,
            )

        if subscription.next_payment_at - timedelta(days=1) > utc_now:
            raise ValidationException(
                translation(
                    request.user.language,
                    en="Your current installment is not due yet",
                    es="Tu cuota actual no está vencida",
                    slug="installment-is-not-due",
                ),
                code=400,
            )

        tasks.charge_plan_financing.delay(plan_financing_id)

        return Response({"status": "loading"}, status=status.HTTP_202_ACCEPTED)


class AcademySubscriptionView(APIView):

    extensions = APIViewExtensions(sort="-id", paginate=True, cache=SubscriptionCache, cache_per_user=True)

    @capable_of("read_subscription")
    def get(self, request, subscription_id=None, academy_id=None):
        handler = self.extensions(request)

        cache = handler.cache.get()
        if cache is not None:
            return cache

        lang = get_user_language(request)
        now = timezone.now()

        if subscription_id:
            item = (
                Subscription.objects.filter(Q(valid_until__gte=now) | Q(valid_until=None), id=subscription_id)
                .exclude(status="DEPRECATED")
                .exclude(status="PAYMENT_ISSUE")
                .exclude(status="ERROR")
                .exclude(status="EXPIRED")
                .exclude(Q(status="CANCELLED") & (Q(next_payment_at__lt=now) | Q(valid_until__lt=now)))
                .select_related('subscriptionbillingteam')
                .prefetch_related('subscriptionbillingteam__seats')
                .first()
            )

            if not item:
                raise ValidationException(
                    translation(lang, en="Subscription not found", es="No existe el suscripción", slug="not-found"),
                    code=404,
                )

            serializer = GetSubscriptionSerializer(item, many=False)
            return handler.response(serializer.data)

        items = Subscription.objects.filter(Q(valid_until__gte=now) | Q(valid_until=None))

        if status := request.GET.get("status"):
            items = items.filter(status__in=status.split(","))
        else:
            items = (
                items.exclude(status="DEPRECATED")
                .exclude(status="PAYMENT_ISSUE")
                .exclude(status="ERROR")
                .exclude(status="EXPIRED")
                .exclude(Q(status="CANCELLED") & (Q(next_payment_at__lt=now) | Q(valid_until__lt=now)))
            )

        if invoice_param := request.GET.get("invoice"):
            values = invoice_param.split(",")
            # Check if all values are numeric (IDs) or strings (slugs)
            if all(v.strip().isdigit() for v in values):
                items = items.filter(invoices__id__in=[int(v) for v in values])
            else:
                items = items.filter(invoices__slug__in=values)

        if service_param := request.GET.get("service"):
            values = service_param.split(",")
            # Check if all values are numeric (IDs) or strings (slugs)
            if all(v.strip().isdigit() for v in values):
                items = items.filter(services__id__in=[int(v) for v in values])
            else:
                items = items.filter(services__slug__in=values)

        if plan_param := request.GET.get("plan"):
            values = plan_param.split(",")
            # Check if all values are numeric (IDs) or strings (slugs)
            if all(v.strip().isdigit() for v in values):
                items = items.filter(plans__id__in=[int(v) for v in values])
            else:
                items = items.filter(plans__slug__in=values)

        if user_id := request.GET.get("users"):
            items = items.filter(user__id=int(user_id))

        # Optimize query to include billing team for seat information
        items = items.select_related('subscriptionbillingteam').prefetch_related('subscriptionbillingteam__seats')

        items = handler.queryset(items)

        serializer = GetAbstractIOweYouSmallSerializer(items, many=True)

        return handler.response(serializer.data)

    def put(self, request, subscription_id, academy_id=None):
        lang = get_user_language(request)

        if not (subscription := Subscription.objects.filter(id=subscription_id).first()):
            raise ValidationException(
                translation(lang, en="Subscription not found", es="No existe la suscripción", slug="not-found"),
                code=404,
            )

        def update_subscription(subscription, data):
            valid_statuses = [choice[0] for choice in Subscription._meta.get_field("status").choices]
            allowed_fields = ["status", "valid_until", "plan"]

            for field, value in data.items():
                if field == "status" and value not in valid_statuses:
                    raise ValidationException(
                        translation(
                            lang,
                            en=f"{field}: '{value}' is not a valid choice.",
                            es=f"{field}: '{value}' no es una opción válida.",
                            slug="invalid-choice",
                        ),
                        code=400,
                    )
                if field in allowed_fields:
                    setattr(subscription, field, value)

        if isinstance(request.data, list):
            for data in request.data:
                update_subscription(subscription, data)
        else:
            update_subscription(subscription, request.data)

        subscription.save()

        return Response({"detail": "Subscription updated successfully"}, status=status.HTTP_200_OK)


class AcademyPlanFinancingView(APIView):

    extensions = APIViewExtensions(sort="-id", paginate=True, cache=PlanFinancingCache, cache_per_user=True)

    def get(self, request, financing_id=None, academy_id=None):
        handler = self.extensions(request)

        # Check cache first to avoid expensive database queries
        cache = handler.cache.get()
        if cache is not None:
            logger.info(f"AcademyPlanFinancingView: Returning cached data for user {request.user.id}")
            return cache

        lang = get_user_language(request)
        now = timezone.now()

        if financing_id:
            item = PlanFinancing.objects.filter(valid_until__gte=now, id=financing_id).first()

            if not item:
                raise ValidationException(
                    translation(
                        lang, en="Plan financing not found", es="No existe el plan de financiamiento", slug="not-found"
                    ),
                    code=404,
                )

            serializer = GetPlanFinancingSerializer(item, many=False)
            return handler.response(serializer.data)

        # Optimize query with select_related and prefetch_related
        items = (
            PlanFinancing.objects.select_related("user", "plan", "currency")
            .prefetch_related("invoices")
            .annotate(fulfilled_invoices_count=Count("invoices", filter=Q(invoices__status="FULFILLED")))
            .filter(Q(valid_until__gte=now) | Q(fulfilled_invoices_count__gte=F("how_many_installments")))
        )

        if user_id := request.GET.get("users"):
            items = items.filter(user__id=int(user_id))

        if invoice_param := request.GET.get("invoice"):
            values = invoice_param.split(",")
            # Check if all values are numeric (IDs) or strings (slugs)
            if all(v.strip().isdigit() for v in values):
                items = items.filter(invoices__id__in=[int(v) for v in values])
            else:
                items = items.filter(invoices__slug__in=values)

        if plan_param := request.GET.get("plan"):
            values = plan_param.split(",")
            # Check if all values are numeric (IDs) or strings (slugs)
            if all(v.strip().isdigit() for v in values):
                items = items.filter(plans__id__in=[int(v) for v in values])
            else:
                items = items.filter(plans__slug__in=values)

        # Apply pagination and sorting
        items = handler.queryset(items)

        serializer = GetAbstractIOweYouSmallSerializer(items, many=True)

        return handler.response(serializer.data)

    def put(self, request, financing_id, academy_id=None):
        lang = get_user_language(request)

        if not financing_id:
            raise ValidationException(
                translation(lang, en="Missing financing_id", es="Falta el ID del financiamiento", slug="missing-id"),
                code=400,
            )

        financing = PlanFinancing.objects.filter(id=financing_id).first()

        if not financing:
            raise ValidationException(
                translation(
                    lang, en="Plan financing not found", es="No existe el plan de financiamiento", slug="not-found"
                ),
                code=404,
            )

        allowed_fields = [
            "next_payment_at",
            "valid_until",
            "plan_expires_at",
            "monthly_price",
            "how_many_installments",
            "status",
        ]

        def update_financing(financing, data):
            for field, value in data.items():
                if field in allowed_fields:
                    setattr(financing, field, value)

        if isinstance(request.data, list):
            for data in request.data:
                update_financing(financing, data)
        else:
            update_financing(financing, request.data)

        financing.save()

        return Response({"detail": "Plan financing updated successfully"}, status=status.HTTP_200_OK)


class MeInvoiceView(APIView):
    extensions = APIViewExtensions(sort="-id", paginate=True)

    def get(self, request, invoice_id=None):
        handler = self.extensions(request)
        lang = get_user_language(request)

        if invoice_id:
            item = Invoice.objects.filter(id=invoice_id, user=request.user).first()

            if not item:
                raise ValidationException(
                    translation(lang, en="Invoice not found", es="La factura no existe", slug="not-found"), code=404
                )

            serializer = GetInvoiceSerializer(item, many=False)
            return handler.response(serializer.data)

        items = Invoice.objects.filter(user=request.user)

        if status := request.GET.get("status"):
            items = items.filter(status__in=status.split(","))

        items = handler.queryset(items)
        serializer = GetInvoiceSmallSerializer(items, many=True)

        return handler.response(serializer.data)


class UserCouponView(APIView):
    extensions = APIViewExtensions(sort="-id", paginate=True)

    def get(self, request):
        try:
            user = request.user
            lang = get_user_language(request)

            # Check if the user already has coupons as a seller
            seller = Seller.objects.filter(user=user).first()

            if not seller:
                # Create a new seller for this user
                seller = Seller(
                    name=f"{user.first_name}".strip() or f"User {user.id}",
                    user=user,
                    type=Seller.Partner.INDIVIDUAL,
                    is_active=True,
                )
                seller.save()

            # Get existing coupons for this seller
            coupons = Coupon.objects.filter(seller=seller)

            # If no coupons exist, create one
            if not coupons.exists():

                # Create a unique slug for the coupon
                slug = f"{Coupon.generate_coupon_key(prefix=f"referral")}-{user.id}"

                coupon = Coupon(
                    slug=slug,
                    discount_type=Coupon.Discount.PERCENT_OFF,
                    discount_value=0.1,  # 10% discount
                    referral_type=Coupon.Referral.PERCENTAGE,
                    referral_value=0.1,  # 10% commission
                    auto=False,
                    how_many_offers=-1,  # No limit
                    seller=seller,
                )
                coupon.save()
                # Note: Since we don't specify plans, all plans are available for this
                # coupon, so, for referrals, we control each plan with the bool "exclude_from_referral_program"

                # Reload the coupons
                coupons = Coupon.objects.filter(seller=seller)

            serializer = GetCouponWithPlansSerializer(coupons, many=True)
            return Response(serializer.data)
        except Exception as e:
            print(e)
            raise ValidationException(
                translation(
                    lang, en="Error getting coupons", es="Error al obtener los cupones", slug="error-getting-coupons"
                ),
                code=500,
            )


class MeUserCouponsView(APIView):
    """Get coupons available to the current user (including user-restricted coupons)."""

    extensions = APIViewExtensions(sort="-id", paginate=True)

    def get(self, request):
        """Get all coupons that the current user can use, with validity status."""
        handler = self.extensions(request)
        user = request.user
        utc_now = timezone.now()

        # Get coupons restricted to this user
        user_restricted_coupons = Coupon.objects.filter(
            Q(offered_at=None) | Q(offered_at__lte=utc_now),
            Q(expires_at=None) | Q(expires_at__gte=utc_now),
            allowed_user=user,
        ).exclude(how_many_offers=0)

        plan = request.GET.get("plan")
        if plan:
            plan = Plan.objects.get(slug=plan)
        else:
            # NO_REFERRAL coupons doesn't should have any plans because it works for all of them, so use any
            plan = Plan.objects.first()
        slugs = list(user_restricted_coupons.values_list("slug", flat=True))

        valid_coupons = get_available_coupons(plan=plan, coupons=slugs, user=user, only_sent_coupons=True)
        valid_coupon_ids = {coupon.id for coupon in valid_coupons}

        coupons = handler.queryset(user_restricted_coupons)
        # Mark each coupon as valid or invalid
        for coupon in coupons:
            coupon._is_valid = coupon.id in valid_coupon_ids
        # Convert to list to ensure evaluation
        coupons_list = list(coupons)
        serializer = GetCouponSerializer(coupons_list, many=True)

        # Add is_valid field to each coupon in the response
        for i, coupon_data in enumerate(serializer.data):
            coupon_data["is_valid"] = getattr(coupons_list[i], "_is_valid", False)

        return handler.response(serializer.data)

    def put(self, request, coupon_slug):
        """Activate automatic application of a user's coupon."""
        lang = get_user_language(request)
        user = request.user

        # Buscar el cupón del usuario
        coupon = Coupon.objects.filter(slug=coupon_slug, allowed_user=user).first()

        if not coupon:
            raise ValidationException(
                translation(
                    lang,
                    en=f"Coupon {coupon_slug} not found",
                    es=f"Cupón {coupon_slug} no encontrado",
                    slug="coupon-not-found",
                ),
                code=404,
            )
        coupon.auto = not coupon.auto
        coupon.save()

        return Response(
            {
                "coupon_slug": coupon.slug,
                "auto": coupon.auto,
            }
        )


class AcademyInvoiceView(APIView):
    extensions = APIViewExtensions(sort="-id", paginate=True)

    @capable_of("read_invoice")
    def get(self, request, invoice_id=None, academy_id=None):
        handler = self.extensions(request)
        lang = get_user_language(request)

        if invoice_id:
            item = Invoice.objects.filter(id=invoice_id, user=request.user, academy__id=academy_id).first()

            if not item:
                raise ValidationException(
                    translation(lang, en="Invoice not found", es="La factura no existe", slug="not-found"), code=404
                )

            serializer = GetInvoiceSerializer(item, many=False)
            return handler.response(serializer.data)

        items = Invoice.objects.filter(user=request.user, academy__id=academy_id)

        if status := request.GET.get("status"):
            items = items.filter(status__in=status.split(","))

        items = handler.queryset(items)
        serializer = GetInvoiceSmallSerializer(items, many=True)

        return handler.response(serializer.data)


class CardView(APIView):
    extensions = APIViewExtensions(sort="-id", paginate=True)

    def post(self, request):
        lang = get_user_language(request)
        academy = get_academy_from_body(request.data, lang=lang, raise_exception=True)

        s = Stripe(academy=academy)
        s.set_language(lang)
        s.add_contact(request.user)

        token = request.data.get("token")
        card_number = request.data.get("card_number")
        exp_month = request.data.get("exp_month")
        exp_year = request.data.get("exp_year")
        cvc = request.data.get("cvc")

        if not ((card_number and exp_month and exp_year and cvc) or token):
            raise ValidationException(
                translation(
                    lang,
                    en="Missing card information",
                    es="Falta la información de la tarjeta",
                    slug="missing-card-information",
                ),
                code=404,
            )

        try:
            if not token:
                token = s.create_card_token(card_number, exp_month, exp_year, cvc)

            s.add_payment_method(request.user, token)

        except ValidationException as e:
            raise e

        except PaymentException as e:
            raise e

        except Exception as e:
            raise ValidationException(str(e), code=400)

        return Response({"status": "ok"})


class V2CardView(APIView):
    extensions = APIViewExtensions(sort="-id", paginate=True)

    def get(self, request):
        """
        Get payment method information for the authenticated user.

        Query Parameters:
            - academy_id (required): Academy to check payment method for.

        Returns:
            200: Payment method information
            {
                "has_payment_method": true,
                "card_last4": "4242",
                "card_brand": "Visa",
                "card_exp_month": 12,
                "card_exp_year": 2025
            }
        """
        lang = get_user_language(request)
        academy = get_academy_from_body(request.query_params.dict(), lang=lang, raise_exception=False)

        if not academy:
            raise ValidationException(
                translation(
                    lang,
                    en="An academy organization must be specified in order to retrieve payment information for the contact",
                    es="Se debe especificar una organización de academia para recuperar la información de pago del contacto",
                    slug="academy-required",
                ),
                code=400,
            )

        # Return info for specific academy
        s = Stripe(academy=academy)
        s.set_language(lang)
        info = s.get_payment_method_info(request.user)

        if info:
            return Response(info)

        return Response({"has_payment_method": False})

    def post(self, request):
        lang = get_user_language(request)
        academy = get_academy_from_body(request.data, lang=lang, raise_exception=False)

        s = Stripe(academy=academy)
        s.set_language(lang)

        token = request.data.get("token")
        card_number = request.data.get("card_number")
        exp_month = request.data.get("exp_month")
        exp_year = request.data.get("exp_year")
        cvc = request.data.get("cvc")

        if not ((card_number and exp_month and exp_year and cvc) or token):
            raise ValidationException(
                translation(
                    lang,
                    en="Missing card information",
                    es="Falta la información de la tarjeta",
                    slug="missing-card-information",
                ),
                code=404,
            )

        if academy:
            s.add_contact(request.user)

        try:
            if not token:
                token = s.create_card_token(card_number, exp_month, exp_year, cvc)

            success, errors, details = s.update_all_payment_methods(
                user=request.user, token=token, card_number=card_number, exp_month=exp_month, exp_year=exp_year, cvc=cvc
            )

            if not success:
                raise ValidationException(
                    translation(
                        lang,
                        en="Failed to update payment method",
                        es="Error al actualizar el método de pago",
                        slug="payment-method-update-failed",
                    ),
                    code=400,
                )

        except ValidationException as e:
            raise e
        except PaymentException as e:
            raise e
        except Exception as e:
            raise ValidationException(str(e), code=400)

        return Response({"status": "ok", "details": details})


class ServiceBlocked(APIView):

    def get(self, request):
        user = request.user

        # mentorship_services = MentorshipService.objects.all()
        from breathecode.payments.flags import blocked_user_ids

        fields = ["from_academy", "from_cohort", "from_mentorship_service"]

        blocked_services = {
            "mentorship-service": {
                "from_everywhere": False,
                "from_academy": [],
                "from_cohort": [],
                "from_mentorship_service": [],
            }
        }

        blocked_services["mentorship-service"]["from_everywhere"] = (
            True if user.id in blocked_user_ids["mentorship-service"]["from_everywhere"] else False
        )

        for field in fields:
            blocked_ids = blocked_user_ids["mentorship-service"][field]
            blocked_services["mentorship-service"][field] = [slug for id_, slug in blocked_ids if id_ == user.id]

        return Response(blocked_services, status=status.HTTP_200_OK)


class ConsumeView(APIView):
    extensions = APIViewExtensions(sort="-id", paginate=True)

    def get(self, request, service_slug):
        handler = self.extensions(request)
        lang = get_user_language(request)

        if not (service := Service.objects.filter(slug=service_slug).first()):
            raise ValidationException(
                translation(lang, en="Service not found", es="Servicio no encontrado", slug="service-not-found"),
                code=404,
            )

        items = ConsumptionSession.objects.filter(consumable__service_item__service=service, user=request.user)

        if status := request.GET.get("status"):
            items = items.filter(status__in=status.split(","))

        items = handler.queryset(items)
        serializer = GetConsumptionSessionSerializer(items, many=True)

        return Response(serializer.data)

    def put(self, request, service_slug, hash=None):
        lang = get_user_language(request)

        force_create = hash is None

        if force_create is False:
            session = ConsumptionSession.get_session(request)
            if session:
                return Response({"id": session.id, "status": "ok"}, status=status.HTTP_200_OK)

        consumables = Consumable.list(user=request.user, lang=lang, service=service_slug, service_type="VOID")

        consumables = discount_consumption_sessions(consumables)
        if consumables.count() == 0:
            raise PaymentException(
                translation(lang, en="Insuficient credits", es="Créditos insuficientes", slug="insufficient-credits")
            )

        consumable = consumables.first()

        session_duration = consumable.service_item.service.session_duration or timedelta(minutes=1)
        session = ConsumptionSession.build_session(
            request,
            consumable,
            session_duration,
            operation_code="unsafe-consume-service-set",
            force_create=force_create,
        )

        session.will_consume(1)

        return Response({"id": session.id, "status": "ok"}, status=status.HTTP_201_CREATED)


class AppConsumeView(ConsumeView):
    permission_classes = [AllowAny]

    # created for mocking purposes
    def get_user(self, request: LinkedHttpRequest):
        return request.get_user()

    @scope(["read:consumable"])
    def put(self, request: LinkedHttpRequest, app: LinkedApp, token: LinkedToken, service_slug, hash=None):
        request.user = self.get_user(request)
        if request.user is None or request.user.is_anonymous:
            raise ValidationException("User not provided", code=400)

        return super().put(request, service_slug, hash)


class CancelConsumptionView(APIView):

    def put(self, request, service_slug, consumptionsession_id):
        lang = get_user_language(request)

        session = (
            ConsumptionSession.objects.filter(
                id=consumptionsession_id,
                consumable__user=request.user,
                consumable__service_item__service__type=Service.Type.VOID,
            )
            .exclude(status="CANCELLED")
            .first()
        )
        if session is None:
            raise ValidationException(
                translation(lang, en="Session not found", es="Sesión no encontrada", slug="session-not-found"),
                code=status.HTTP_404_NOT_FOUND,
            )

        how_many = session.how_many
        consumable = session.consumable
        reimburse_service_units.send_robust(instance=consumable, sender=consumable.__class__, how_many=how_many)

        session.status = session.Status.CANCELLED
        session.save()

        return Response({"id": session.id, "status": "reversed"}, status=status.HTTP_200_OK)


class AppCancelConsumptionView(CancelConsumptionView):
    permission_classes = [AllowAny]

    # created for mocking purposes
    def get_user(self, request: LinkedHttpRequest):
        return request.get_user()

    @scope(["read:consumable"])
    def put(self, request: LinkedHttpRequest, app: LinkedApp, token: LinkedToken, service_slug, consumptionsession_id):
        request.user = self.get_user(request)
        if request.user is None or request.user.is_anonymous:
            raise ValidationException("User not provided", code=400)

        return super().put(request, service_slug, consumptionsession_id)


class PlanOfferView(APIView):
    permission_classes = [AllowAny]
    extensions = APIViewExtensions(cache=PlanOfferCache, sort="-id", paginate=True)

    def get_lookup(self, key, value):
        args = ()
        kwargs = {}
        slug_key = f"{key}__slug__in"
        pk_key = f"{key}__id__in"

        for v in value.split(","):
            if slug_key not in kwargs and not v.isnumeric():
                kwargs[slug_key] = []

            if pk_key not in kwargs and v.isnumeric():
                kwargs[pk_key] = []

            if v.isnumeric():
                kwargs[pk_key].append(int(v))

            else:
                kwargs[slug_key].append(v)

        if len(kwargs) > 1:
            args = (Q(**{slug_key: kwargs[slug_key]}) | Q(**{pk_key: kwargs[pk_key]}),)
            kwargs = {}

        return args, kwargs

    def get(self, request):
        handler = self.extensions(request)

        cache = handler.cache.get()
        if cache is not None:
            return cache

        lang = get_user_language(request)
        utc_now = timezone.now()

        # do no show the bags of type preview they are build
        items = PlanOffer.objects.filter(Q(expires_at=None) | Q(expires_at__gt=utc_now))

        if suggested_plan := request.GET.get("suggested_plan"):
            args, kwargs = self.get_lookup("suggested_plan", suggested_plan)
            items = items.filter(*args, **kwargs)

        if original_plan := request.GET.get("original_plan"):
            args, kwargs = self.get_lookup("original_plan", original_plan)
            items = items.filter(*args, **kwargs)

        items = items.distinct()
        items = handler.queryset(items)
        items = items.annotate(lang=Value(lang, output_field=CharField()))
        serializer = GetPlanOfferSerializer(items, many=True)

        return handler.response(serializer.data)


class CouponBaseView(APIView):

    def get_coupons(self, only_sent_coupons: bool = False) -> list[Coupon]:
        plan_pk: str = self.request.GET.get("plan")
        if not plan_pk:
            raise ValidationException(
                translation(
                    get_user_language(self.request),
                    en="Missing plan in query string",
                    es="Falta el plan en la consulta",
                    slug="missing-plan",
                ),
                code=404,
            )

        extra = {}
        if plan_pk.isnumeric():
            extra["id"] = int(plan_pk)

        else:
            extra["slug"] = plan_pk

        plan = Plan.objects.filter(**extra).first()
        if not plan:
            raise ValidationException(
                translation(
                    get_user_language(self.request), en="Plan not found", es="El plan no existe", slug="plan-not-found"
                ),
                code=404,
            )

        coupon_codes = self.request.GET.get("coupons", "")
        if coupon_codes:
            coupon_codes = coupon_codes.split(",")
        else:
            coupon_codes = []

        return get_available_coupons(
            plan, coupons=coupon_codes, user=self.request.user, only_sent_coupons=only_sent_coupons
        )


class CouponView(CouponBaseView):
    permission_classes = [AllowAny]

    def get(self, request):
        coupons = self.get_coupons()
        serializer = GetCouponSerializer(coupons, many=True)

        return Response(serializer.data)


class BagCouponView(CouponBaseView):

    def put(self, request, bag_id):
        lang = get_user_language(request)
        coupons = self.get_coupons(only_sent_coupons=True)

        # do no show the bags of type preview they are build
        client = None
        if IS_DJANGO_REDIS:
            client = get_redis_connection("default")

        try:
            with Lock(client, f"lock:bag:user-{request.user.email}", timeout=30, blocking_timeout=30):
                bag = Bag.objects.filter(
                    id=bag_id, user=request.user, status="CHECKING", type__in=["BAG", "PREVIEW"]
                ).first()
                if bag is None:
                    raise ValidationException(
                        translation(lang, en="Bag not found", es="Bolsa no encontrada", slug="bag-not-found"),
                        code=status.HTTP_404_NOT_FOUND,
                    )

                bag.coupons.set(coupons)

        except LockError:
            raise ValidationException(
                translation(
                    lang,
                    en="Timeout reached, operation timed out.",
                    es="Tiempo de espera alcanzado, operación agotada.",
                    slug="timeout",
                ),
                code=408,
            )

        serializer = GetBagSerializer(bag, many=False)
        return Response(serializer.data, status=status.HTTP_200_OK)


class BagView(APIView):
    extensions = APIViewExtensions(sort="-id", paginate=True)

    def get(self, request):
        handler = self.extensions(request)

        # do no show the bags of type preview they are build
        items = Bag.objects.filter(user=request.user, type="BAG")

        if status := request.GET.get("status"):
            items = items.filter(status__in=status.split(","))
        else:
            items = items.filter(status="CHECKING")

        items = handler.queryset(items)
        serializer = GetBagSerializer(items, many=True)

        return handler.response(serializer.data)

    def put(self, request):
        lang = get_user_language(request)
        academy = get_academy_from_body(request.data, lang=lang, raise_exception=True)

        s = Stripe(academy=academy)
        s.set_language(lang)
        s.add_contact(request.user)

        if "coupons" in request.data and not isinstance(request.data["coupons"], list):
            raise ValidationException(
                translation(
                    lang,
                    en="Coupons must be a list of strings",
                    es="Cupones debe ser una lista de cadenas",
                    slug="invalid-coupons",
                ),
                code=400,
            )

        if "coupons" in request.data and len(request.data["coupons"]) > (max := max_coupons_allowed()):
            raise ValidationException(
                translation(
                    lang,
                    en=f"Too many coupons (max {max})",
                    es=f"Demasiados cupones (max {max})",
                    slug="too-many-coupons",
                ),
                code=400,
            )

        # do no show the bags of type preview they are build
        client = None
        if IS_DJANGO_REDIS:
            client = get_redis_connection("default")

        try:
            with Lock(client, f"lock:bag:user-{request.user.email}", timeout=30, blocking_timeout=30):
                bag, _ = Bag.objects.get_or_create(user=request.user, status="CHECKING", type="BAG")

        except LockError:
            raise ValidationException(
                translation(
                    lang,
                    en="Timeout reached, operation timed out.",
                    es="Tiempo de espera alcanzado, operación agotada.",
                    slug="timeout",
                ),
                code=408,
            )

        add_items_to_bag(request, bag, lang)

        plan = bag.plans.first()
        is_free_trial = plan.trial_duration > 0 if plan else False

        # free trial took
        if is_free_trial and Subscription.objects.filter(user=request.user, plans__in=bag.plans.all()).exists():
            is_free_trial = False

        is_free_plan = (
            plan.price_per_month == 0
            and plan.price_per_quarter == 0
            and plan.price_per_half == 0
            and plan.price_per_year == 0
            if plan
            else False
        )
        recurrent = request.data.get("recurrent")

        if is_free_trial:
            bag.is_recurrent = False
        elif is_free_plan or plan:
            bag.is_recurrent = True
        else:
            bag.is_recurrent = recurrent or False

        bag.save()

        if plan and bag.coupons.count() == 0:
            coupons = get_available_coupons(plan, request.data.get("coupons", []), user=request.user)
            bag.coupons.set(coupons)

        # actions.check_dependencies_in_bag(bag, lang)

        serializer = GetBagSerializer(bag, many=False)
        return Response(serializer.data)

    def delete(self, request):
        # do no show the bags of type preview they are build
        Bag.objects.filter(user=request.user, status="CHECKING", type="BAG").delete()
        return Response(status=204)


class CheckingView(APIView):
    extensions = APIViewExtensions(sort="-id", paginate=True)

    def put(self, request):
        bag_type = request.data.get("type", "BAG").upper()
        created = False
        country_code = request.data.get("country_code")

        lang = get_user_language(request)

        # Validate supported bag types early to avoid using an uninitialized 'bag'
        if bag_type not in {"BAG", "PREVIEW"}:
            raise ValidationException(
                translation(
                    lang,
                    en="Invalid type. Allowed values are 'BAG' or 'PREVIEW'",
                    es="Tipo inválido. Los valores permitidos son 'BAG' o 'PREVIEW'",
                    slug="invalid-bag-type",
                ),
                code=400,
            )

        client = None
        if IS_DJANGO_REDIS:
            client = get_redis_connection("default")

        try:
            # the lock must wrap the transaction
            with Lock(client, f"lock:bag:user-{request.user.email}", timeout=30, blocking_timeout=30):
                with transaction.atomic():
                    sid = transaction.savepoint()
                    try:
                        if bag_type == "BAG" and not (
                            bag := Bag.objects.filter(user=request.user, status="CHECKING", type=bag_type).first()
                        ):
                            raise ValidationException(
                                translation(lang, en="Bag not found", es="Bolsa no encontrada", slug="not-found"),
                                code=404,
                            )
                        if bag_type == "PREVIEW":

                            academy = request.data.get("academy")
                            kwargs = {}

                            if academy and (isinstance(academy, int) or academy.isnumeric()):
                                kwargs["id"] = int(academy)
                            else:
                                kwargs["slug"] = academy

                            academy = Academy.objects.filter(main_currency__isnull=False, **kwargs).first()

                            if not academy:
                                cohort = request.data.get("cohort")

                                kwargs = {}

                                if cohort and (isinstance(cohort, int) or cohort.isnumeric()):
                                    kwargs["id"] = int(cohort)
                                else:
                                    kwargs["slug"] = cohort

                                cohort = Cohort.objects.filter(academy__main_currency__isnull=False, **kwargs).first()
                                if cohort:
                                    academy = cohort.academy
                                    request.data["cohort"] = cohort.id

                            if not academy and (plans := request.data.get("plans")) and len(plans) == 1:
                                kwargs = {}
                                pk = plans[0]
                                if isinstance(pk, int):
                                    kwargs["id"] = int(pk)

                                else:
                                    kwargs["slug"] = pk

                                plan = Plan.objects.filter(owner__main_currency__isnull=False, **kwargs).first()

                                if plan:
                                    academy = plan.owner

                            if not academy:
                                raise ValidationException(
                                    translation(
                                        lang,
                                        en="Academy not found or not configured properly",
                                        es="Academia no encontrada o no configurada correctamente",
                                        slug="not-found",
                                    ),
                                    code=404,
                                )

                            if "coupons" in request.data and not isinstance(request.data["coupons"], list):
                                raise ValidationException(
                                    translation(
                                        lang,
                                        en="Coupons must be a list of strings",
                                        es="Cupones debe ser una lista de cadenas",
                                        slug="invalid-coupons",
                                    ),
                                    code=400,
                                )

                            if "coupons" in request.data and len(request.data["coupons"]) > (
                                max := max_coupons_allowed()
                            ):
                                raise ValidationException(
                                    translation(
                                        lang,
                                        en=f"Too many coupons (max {max})",
                                        es=f"Demasiados cupones (max {max})",
                                        slug="too-many-coupons",
                                    ),
                                    code=400,
                                )

                            bag, created = Bag.objects.get_or_create(
                                user=request.user,
                                status="CHECKING",
                                type=bag_type,
                                academy=academy,
                                currency=academy.main_currency,
                            )

                            add_items_to_bag(request, bag, lang)

                            plan = bag.plans.first()
                            is_free_trial = plan.trial_duration > 0 if plan else False

                            # free trial took
                            if (
                                is_free_trial
                                and Subscription.objects.filter(user=request.user, plans__in=bag.plans.all()).exists()
                            ):
                                is_free_trial = False

                            is_free_plan = (
                                plan.price_per_month == 0
                                and plan.price_per_quarter == 0
                                and plan.price_per_half == 0
                                and plan.price_per_year == 0
                                if plan
                                else False
                            )
                            recurrent = request.data.get("recurrent")

                            if is_free_trial:
                                bag.is_recurrent = False
                            elif is_free_plan or plan:
                                bag.is_recurrent = True
                            else:
                                bag.is_recurrent = recurrent or False

                            bag.save()

                            if plan and bag.coupons.count() == 0:
                                coupons = get_available_coupons(
                                    plan, request.data.get("coupons", []), user=request.user
                                )
                                bag.coupons.set(coupons)
                            # actions.check_dependencies_in_bag(bag, lang)

                        utc_now = timezone.now()

                        bag.token = Token.generate_key()
                        bag.expires_at = utc_now + timedelta(minutes=60)

                        plan = bag.plans.filter(status="CHECKING").first()

                        # Initialize pricing_ratio_explanation
                        pricing_ratio_explanation = {"plans": [], "service_items": []}

                        # FIXME: the service items should be bought without renewals
                        if not plan or plan.is_renewable:
                            bag.country_code = country_code
                            bag.amount_per_month, bag.amount_per_quarter, bag.amount_per_half, bag.amount_per_year = (
                                get_amount(bag, bag.academy.main_currency, lang)
                            )

                        else:
                            # FIXME
                            actions.ask_to_add_plan_and_charge_it_in_the_bag(bag, request.user, lang)

                        # Save pricing ratio explanation if any ratios were applied
                        if pricing_ratio_explanation["plans"] or pricing_ratio_explanation["service_items"]:
                            bag.pricing_ratio_explanation = pricing_ratio_explanation

                        amount = (
                            bag.amount_per_month or bag.amount_per_quarter or bag.amount_per_half or bag.amount_per_year
                        )
                        plans = bag.plans.all()
                        if not amount and plans.filter(financing_options__id__gte=1):
                            amount = 1

                        if amount == 0 and Subscription.objects.filter(user=request.user, plans__in=plans).count():
                            raise ValidationException(
                                translation(
                                    lang,
                                    en="Your free trial was already took",
                                    es="Tu prueba gratuita ya fue tomada",
                                    slug="your-free-trial-was-already-took",
                                ),
                                code=400,
                            )

                        bag.save()
                        transaction.savepoint_commit(sid)

                        serializer = GetBagSerializer(bag, many=False)
                        return Response(
                            serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
                        )

                    except Exception as e:
                        transaction.savepoint_rollback(sid)
                        raise e

        except LockError:
            raise ValidationException(
                translation(
                    lang,
                    en="Timeout reached, operation timed out.",
                    es="Tiempo de espera alcanzado, operación agotada.",
                    slug="timeout",
                ),
                code=408,
            )


class ConsumableCheckoutView(APIView):
    extensions = APIViewExtensions(sort="-id", paginate=True)

    def post(self, request):
        lang = get_user_language(request)

        service = request.data.get("service")
        total_items = request.data.get("how_many")
        academy = request.data.get("academy")
        country_code = request.data.get("country_code")
        is_team_allowed = request.data.get("is_team_allowed")
        if is_team_allowed is None:
            is_team_allowed = True

        if not service:
            raise ValidationException(
                translation(lang, en="Service is required", es="El servicio es requerido", slug="service-is-required"),
                code=400,
            )
        query = {}
        if service and isinstance(service, int):
            query["id"] = service
        elif service and isinstance(service, str):
            query["slug"] = service

        if not query or not (service := Service.objects.filter(**query).first()):
            raise ValidationException(
                translation(lang, en="Service not found", es="El servicio no fue encontrado", slug="service-not-found")
            )

        if not total_items:
            raise ValidationException(
                translation(
                    lang, en="How many is required", es="La cantidad es requerida", slug="how-many-is-required"
                ),
                code=400,
            )

        if not (isinstance(total_items, int) or isinstance(total_items, float)) or total_items <= 0:
            raise ValidationException(
                translation(
                    lang,
                    en="How many is not valid",
                    es="La cantidad de paquetes no es válida",
                    slug="how-many-is-not-valid",
                ),
                code=400,
            )

        if not academy:
            raise ValidationException(
                translation(lang, en="Academy is required", es="La academia es requerida", slug="academy-is-required"),
                code=400,
            )

        if not Academy.objects.filter(id=academy).exists():
            raise ValidationException(
                translation(lang, en="Academy not found", es="La academia no fue encontrada", slug="academy-not-found")
            )

        mentorship_service_set = request.data.get("mentorship_service_set")
        event_type_set = request.data.get("event_type_set")

        if mentorship_service_set is not None and event_type_set is not None:
            raise ValidationException(
                translation(
                    lang,
                    en="Just can pass Mentorship service set or event type set is required, not both",
                    es="Solo puede pasar Mentoría o tipo de evento, no ambos",
                    slug="mentorship-service-set-or-event-type-set-is-required",
                ),
                code=400,
            )

        if service.type == "MENTORSHIP_SERVICE_SET" and not mentorship_service_set:
            raise ValidationException(
                translation(
                    lang,
                    en="This service is type mentorship service set, but you provided other type of resource",
                    es="Este servicio es de tipo mentoría, pero usted proporcionó otro tipo de recurso",
                    slug="bad-service-type-mentorship-service-set",
                ),
                code=400,
            )

        elif service.type == "EVENT_TYPE_SET" and not event_type_set:
            raise ValidationException(
                translation(
                    lang,
                    en="This service is type event type set, but you provided other type of resource",
                    es="Este servicio es de tipo tipo de evento, pero usted proporcionó otro tipo de recurso",
                    slug="bad-service-type-event-type-set",
                ),
                code=400,
            )

        elif service.type not in ["MENTORSHIP_SERVICE_SET", "EVENT_TYPE_SET", "VOID", "SEAT"]:
            raise ValidationException(
                translation(
                    lang,
                    en="This service can't be bought here yet",
                    es="Este servicio no se puede comprar aquí todavía",
                    slug="service-type-no-implemented",
                ),
                code=400,
            )

        kwargs = {}
        if mentorship_service_set:
            kwargs["available_mentorship_service_sets"] = mentorship_service_set

        elif event_type_set:
            kwargs["available_event_type_sets"] = event_type_set

        academy_service = AcademyService.objects.filter(academy_id=academy, service=service, **kwargs).first()
        if not academy_service and service.type != "SEAT":
            raise ValidationException(
                translation(
                    lang,
                    en="Academy service not found",
                    es="Servicio de academia no encontrado",
                    slug="academy-service-not-found",
                ),
                code=404,
            )

        if is_team_allowed not in [True, False]:
            raise ValidationException(
                translation(
                    lang,
                    en="is_team_allowed must be a boolean",
                    es="is_team_allowed debe ser un booleano",
                    slug="is_team_allowed-must-be-a-boolean",
                ),
                code=400,
            )

        # Seats purchase flow: increase team seats for an existing subscription
        if service.type == "SEAT":
            seats = total_items

            subscription_id = request.data.get("subscription")
            if not subscription_id or not isinstance(subscription_id, int):
                raise ValidationException(
                    translation(
                        lang,
                        en="Subscription is required",
                        es="La suscripción es requerida",
                        slug="subscription-is-required",
                    ),
                    code=400,
                )

            subscription = Subscription.objects.filter(id=subscription_id).first()
            if not subscription:
                raise ValidationException(
                    translation(
                        lang,
                        en="Subscription not found",
                        es="Suscripción no encontrada",
                        slug="subscription-not-found",
                    ),
                    code=404,
                )

            if subscription.user_id != request.user.id:
                raise ValidationException(
                    translation(
                        lang,
                        en="Only the owner can manage seats",
                        es="Solo el dueño puede gestionar asientos",
                        slug="only-owner-allowed",
                    ),
                    code=403,
                )

            plan = subscription.plans.first()
            if not plan or not plan.seat_service_price:
                raise ValidationException(
                    translation(
                        lang,
                        en="Plan does not support team seats",
                        es="Plan no soporta asientos de equipo",
                        slug="plan-does-not-support-team-seats",
                    ),
                    code=400,
                )

            if seats is None:
                raise ValidationException(
                    translation(
                        lang,
                        en="Seats is required to update team capacity",
                        es="Se requieren asientos para actualizar la capacidad del equipo",
                        slug="seats-required",
                    ),
                    code=400,
                )

            created_team = False
            team = SubscriptionBillingTeam.objects.filter(subscription=subscription).first()
            current_limit = team.additional_seats if team else 0
            desired_limit = seats
            delta = desired_limit - current_limit

            if delta <= 0:
                # TODO: in a future you should decrease the seats limit and return a invoice with no amount
                raise ValidationException(
                    translation(
                        lang,
                        en="Desired seats must be greater than current seats",
                        es="Los asientos deseados deben ser mayores que los asientos actuales",
                        slug="desired-seats-must-be-greater",
                    ),
                    code=400,
                )

            # use seat service pricing set on plan
            academy_service = plan.seat_service_price

            # price seats delta with pricing ratios
            amount, currency, pricing_ratio_explanation = academy_service.get_discounted_price(delta, country_code)

            if amount <= 0.5:
                raise ValidationException(
                    translation(
                        lang,
                        en="The amount is too low",
                        es="El monto es muy bajo",
                        slug="the-amount-is-too-low",
                    ),
                    code=400,
                )

            academy = subscription.academy
            s = Stripe(academy=academy)

            invoice = None
            with transaction.atomic():
                sid = transaction.savepoint()
                try:
                    s.set_language(lang)
                    s.add_contact(request.user)

                    # keeps this inside a transaction
                    bag = Bag(
                        type="CHARGE",
                        status="PAID",
                        was_delivered=True,
                        user=request.user,
                        currency=currency,
                        academy=academy,
                        is_recurrent=False,
                        country_code=country_code,
                        pricing_ratio_explanation=pricing_ratio_explanation,
                    )
                    if pricing_ratio_explanation and pricing_ratio_explanation.get("service_items"):
                        bag.pricing_ratio_explanation = pricing_ratio_explanation

                    bag.save()

                    description = f"Increase team seats by {int(delta)} (to {int(desired_limit)})"
                    invoice = s.pay(
                        request.user,
                        bag,
                        amount,
                        currency=bag.currency.code.lower(),
                        description=description,
                        subscription_billing_team=team,
                    )

                    # Ensure billing team exists and update seats limit
                    if not team:
                        created_team = True
                        # Add +1 seat for owner (first seat is free)
                        team = SubscriptionBillingTeam.objects.create(
                            subscription=subscription,
                            name=f"Team {subscription.id}",
                            additional_seats=desired_limit,
                            consumption_strategy=(
                                plan.consumption_strategy
                                if plan.consumption_strategy != Plan.ConsumptionStrategy.BOTH
                                else Plan.ConsumptionStrategy.PER_SEAT
                            ),
                        )

                        service_item, _ = ServiceItem.get_or_create_for_service(
                            service=service,
                            how_many=desired_limit,
                            is_team_allowed=True,
                        )

                        # mark subscription has billing team
                        subscription.has_billing_team = True
                        subscription.seat_service_item = service_item
                        subscription.save(update_fields=["has_billing_team", "seat_service_item"])

                        # add owner as first seat
                        seat, _ = SubscriptionSeat.objects.get_or_create(
                            billing_team=team,
                            user=subscription.user,
                            email=(subscription.user.email or "").strip().lower(),
                            defaults={"is_active": True},
                        )

                        # migrate existing consumables with support for team seats
                        existing_consumables = Consumable.objects.filter(
                            subscription=subscription,
                            user=subscription.user,
                            service_item__is_team_allowed=True,
                        )

                        if plan.consumption_strategy == Plan.ConsumptionStrategy.PER_TEAM:
                            existing_consumables.update(
                                user=None,
                                subscription_billing_team=team,
                            )

                        else:
                            existing_consumables.update(
                                subscription_seat=seat,
                                subscription_billing_team=team,
                            )

                    else:
                        # update seats limit and log
                        try:
                            seats_log = team.seats_log or []
                        except Exception:
                            seats_log = []
                        seats_log.append(
                            {
                                "action": "LIMIT_UPDATED",
                                "from": int(current_limit),
                                "to": int(desired_limit),
                                "created_at": timezone.now().isoformat().replace("+00:00", "Z"),
                            }
                        )
                        team.seats_log = seats_log
                        team.additional_seats = desired_limit
                        team.consumption_strategy = (
                            plan.consumption_strategy
                            if plan.consumption_strategy != Plan.ConsumptionStrategy.BOTH
                            else Plan.ConsumptionStrategy.PER_SEAT
                        )
                        team.save(update_fields=["seats_log", "additional_seats", "consumption_strategy"])

                    if created_team:
                        tasks.build_service_stock_scheduler_from_subscription.delay(subscription.id)

                    tasks_activity.add_activity.delay(
                        request.user.id,
                        "checkout_completed",
                        related_type="payments.Invoice",
                        related_id=invoice.id,
                    )

                except Exception as e:
                    if invoice:
                        s.set_language(lang)
                        s.refund_payment(invoice)

                    transaction.savepoint_rollback(sid)
                    raise e

                transaction.savepoint_commit(sid)

            serializer = GetInvoiceSerializer(invoice, many=False)
            return Response(serializer.data, status=201)

        # Default flow: buy consumables for mentorship/events
        academy_service.validate_transaction(total_items, lang)
        amount, currency, pricing_ratio_explanation = academy_service.get_discounted_price(total_items, country_code)

        if amount <= 0.5:
            raise ValidationException(
                translation(lang, en="The amount is too low", es="El monto es muy bajo", slug="the-amount-is-too-low"),
                code=400,
            )

        academy = get_academy_from_body(request.data, lang=lang, raise_exception=True)
        s = Stripe(academy=academy)

        invoice = None
        with transaction.atomic():
            sid = transaction.savepoint()
            try:
                s.set_language(lang)
                s.add_contact(request.user)
                service_item, _ = ServiceItem.get_or_create_for_service(
                    service=service, how_many=total_items, is_team_allowed=is_team_allowed
                )

                # keeps this inside a transaction
                bag = Bag(
                    type="CHARGE",
                    status="PAID",
                    was_delivered=True,
                    user=request.user,
                    currency=currency,
                    academy=academy,
                    is_recurrent=False,
                    country_code=country_code,  # Store the country code for future reference
                    pricing_ratio_explanation=pricing_ratio_explanation,
                )

                # Store pricing ratio explanation if any ratios were applied
                if pricing_ratio_explanation["service_items"]:
                    bag.pricing_ratio_explanation = pricing_ratio_explanation

                bag.save()

                if mentorship_service_set:
                    mentorship_service_set = MentorshipServiceSet.objects.filter(id=mentorship_service_set).first()

                if event_type_set:
                    event_type_set = EventTypeSet.objects.filter(id=event_type_set).first()

                bag.service_items.add(service_item)

                if mentorship_service_set:
                    description = f"Can join to {int(total_items)} mentorships"

                else:
                    description = f"Can join to {int(total_items)} events"

                invoice = s.pay(request.user, bag, amount, currency=bag.currency.code.lower(), description=description)

                consumable = Consumable(
                    service_item=service_item,
                    user=request.user,
                    how_many=total_items,
                    mentorship_service_set=mentorship_service_set,
                    event_type_set=event_type_set,
                )

                consumable.save()

                tasks_activity.add_activity.delay(
                    request.user.id,
                    "checkout_completed",
                    related_type="payments.Invoice",
                    related_id=invoice.id,
                )

            except Exception as e:
                if invoice:
                    s.set_language(lang)
                    s.refund_payment(invoice)

                transaction.savepoint_rollback(sid)
                raise e

        serializer = GetInvoiceSerializer(invoice, many=False)
        return Response(serializer.data, status=201)


class PayView(APIView):
    extensions = APIViewExtensions(sort="-id", paginate=True)

    def post(self, request):
        utc_now = timezone.now()
        lang = get_user_language(request)

        conversion_info = request.data["conversion_info"] if "conversion_info" in request.data else None
        validate_conversion_info(conversion_info, lang)

        conversion_info = str(conversion_info) if conversion_info is not None else ""

        with transaction.atomic():
            sid = transaction.savepoint()
            try:

                reputation, _ = FinancialReputation.objects.get_or_create(user=request.user)

                current_reputation = reputation.get_reputation()
                if current_reputation == "FRAUD" or current_reputation == "BAD":
                    raise PaymentException(
                        translation(
                            lang,
                            en="The payment could not be completed because you have a bad reputation on this platform",
                            es="No se pudo completar el pago porque tienes mala reputación en esta plataforma",
                        ),
                        slug="fraud-or-bad-reputation",
                        silent=True,
                    )

                # do no show the bags of type preview they are build
                # type = request.data.get('type', 'BAG').upper()
                token = request.data.get("token")
                if not token:
                    raise ValidationException(
                        translation(
                            lang, en="Invalid bag token", es="El token de la bolsa es inválido", slug="missing-token"
                        ),
                        code=404,
                    )

                recurrent = request.data.get("recurrent", False)
                bag = Bag.objects.filter(
                    user=request.user,
                    status="CHECKING",
                    token=token,
                    academy__main_currency__isnull=False,
                    expires_at__gte=utc_now,
                ).first()

                if not bag:
                    raise ValidationException(
                        translation(
                            lang,
                            en="Bag not found, maybe you need to renew the checking",
                            es="Bolsa no encontrada, quizás necesitas renovar el checking",
                            slug="not-found-or-without-checking",
                        ),
                        code=404,
                    )

                if bag.service_items.count() == 0 and bag.plans.count() == 0:
                    raise ValidationException(
                        translation(lang, en="Bag is empty", es="La bolsa esta vacía", slug="bag-is-empty"), code=400
                    )

                how_many_installments = request.data.get("how_many_installments")
                chosen_period = request.data.get("chosen_period", "").upper()

                available_for_free_trial = False
                available_free = False
                if not how_many_installments and not chosen_period:
                    available_for_free_trial = (
                        bag.amount_per_month == 0
                        and bag.amount_per_quarter == 0
                        and bag.amount_per_half == 0
                        and bag.amount_per_year == 0
                    )

                    plan = bag.plans.first()
                    available_for_free_trial = available_for_free_trial and (
                        not plan.financing_options.filter().exists() if plan else False
                    )

                    available_free = available_for_free_trial and not plan.trial_duration
                    available_for_free_trial = available_for_free_trial and plan.trial_duration

                if (
                    not available_for_free_trial
                    and not available_free
                    and not how_many_installments
                    and not chosen_period
                ):
                    raise ValidationException(
                        translation(
                            lang,
                            en="Missing chosen period",
                            es="Falta el periodo elegido",
                            slug="missing-chosen-period",
                        ),
                        code=400,
                    )

                available_chosen_periods = ["MONTH", "QUARTER", "HALF", "YEAR"]
                if (
                    not available_for_free_trial
                    and not available_free
                    and not how_many_installments
                    and chosen_period not in available_chosen_periods
                ):
                    raise ValidationException(
                        translation(
                            lang,
                            en=f"Invalid chosen period ({', '.join(available_chosen_periods)})",
                            es=f"Periodo elegido inválido ({', '.join(available_chosen_periods)})",
                            slug="invalid-chosen-period",
                        ),
                        code=400,
                    )

                if (
                    not available_for_free_trial
                    and not available_free
                    and not chosen_period
                    and (not isinstance(how_many_installments, int) or how_many_installments <= 0)
                ):
                    raise ValidationException(
                        translation(
                            lang,
                            en="how_many_installments must be a positive number greather than 0",
                            es="how_many_installments debe ser un número positivo mayor a 0",
                            slug="invalid-how-many-installments",
                        ),
                        code=400,
                    )

                if "coupons" in request.data and not isinstance(request.data["coupons"], list):
                    raise ValidationException(
                        translation(
                            lang,
                            en="Coupons must be a list of strings",
                            es="Cupones debe ser una lista de cadenas",
                            slug="invalid-coupons",
                        ),
                        code=400,
                    )

                if not available_for_free_trial and not available_free and not chosen_period and how_many_installments:
                    bag.how_many_installments = how_many_installments

                coupons = bag.coupons.none()

                if not available_for_free_trial and not available_free and bag.how_many_installments > 0:
                    try:
                        plan = bag.plans.filter().first()
                        option = plan.financing_options.filter(how_many_months=bag.how_many_installments).first()
                        original_price = option.monthly_price

                        # Apply pricing ratio first
                        adjusted_price, _, c = apply_pricing_ratio(original_price, bag.country_code, option)

                        if c and c.code != bag.currency.code:
                            bag.currency = c
                            bag.save()

                        # Initialize add-ons to zero by default
                        add_ons_amount = 0
                        if request.data.get("add_ons"):
                            add_ons_amount = actions.manage_plan_financing_add_ons(request, bag, lang)

                        adjusted_price += add_ons_amount

                        # Then apply coupons
                        coupons = bag.coupons.all()
                        amount = get_discounted_price(adjusted_price, coupons)

                    except Exception:
                        raise ValidationException(
                            translation(
                                lang,
                                en="Bag bad configured, related to financing option",
                                es="La bolsa esta mal configurada, relacionado a la opción de financiamiento",
                                slug="invalid-bag-configured-by-installments",
                            ),
                            code=500,
                        )

                elif not available_for_free_trial and not available_free:
                    amount = get_amount_by_chosen_period(bag, chosen_period, lang)
                    coupons = bag.coupons.all()
                    original_price = amount
                    amount = get_discounted_price(amount, coupons)

                else:
                    original_price = 0
                    amount = 0

                if (
                    original_price == 0
                    and Subscription.objects.filter(user=request.user, plans__in=bag.plans.all()).count()
                ):
                    raise ValidationException(
                        translation(
                            lang,
                            en="Your free trial was already took",
                            es="Tu prueba gratuita ya fue tomada",
                            slug="your-free-trial-was-already-took",
                        ),
                        code=500,
                    )

                # actions.check_dependencies_in_bag(bag, lang)

                if (
                    original_price == 0
                    and not available_free
                    and available_for_free_trial
                    and not bag.plans.filter(plan_offer_from__id__gte=1).exists()
                ):
                    raise ValidationException(
                        translation(
                            lang,
                            en="The plan was chosen does not have a pricing setup, it's not ready to be sold",
                            es="El plan elegido no tiene una configuracion de precios, no esta listo para venderse",
                            slug="the-plan-was-chosen-is-not-ready-too-be-sold",
                        )
                    )

                if amount >= 0.50:
                    s = Stripe(academy=bag.academy)
                    s.set_language(lang)
                    invoice = s.pay(request.user, bag, amount, currency=bag.currency.code)

                elif amount == 0:
                    invoice = Invoice(
                        user=request.user,
                        amount=0,
                        paid_at=utc_now,
                        bag=bag,
                        status="FULFILLED",
                        currency=bag.currency,
                        academy=bag.academy,
                    )

                    invoice.save()

                else:
                    raise ValidationException(
                        translation(lang, en="Amount is too low", es="El monto es muy bajo", slug="amount-is-too-low"),
                        code=500,
                    )

                # Calculate is_recurrent based on:
                # 1. If it's a free trial -> False
                # 2. If it's a free plan -> True
                # 3. If it has paid plans -> True
                # 4. If only service items -> use user's choice (recurrent parameter)
                is_free_trial = available_for_free_trial
                is_free_plan = available_free
                has_plans = bag.plans.exists()
                plan = bag.plans.first() if has_plans else None

                if is_free_trial:
                    bag.is_recurrent = False
                elif (is_free_plan and plan) or has_plans:
                    bag.is_recurrent = True
                else:
                    bag.is_recurrent = recurrent

                bag.chosen_period = chosen_period or "NO_SET"
                bag.status = "PAID"
                bag.token = None
                bag.expires_at = None
                bag.save()

                # Create reward coupons for sellers if coupons were used
                if coupons.exists() and original_price > 0:
                    actions.create_seller_reward_coupons(list(coupons), original_price, request.user)

                transaction.savepoint_commit(sid)

                if original_price == 0:
                    tasks.build_free_subscription.delay(bag.id, invoice.id, conversion_info=conversion_info)

                elif bag.how_many_installments > 0:
                    tasks.build_plan_financing.delay(bag.id, invoice.id, conversion_info=conversion_info)

                else:
                    tasks.build_subscription.delay(bag.id, invoice.id, conversion_info=conversion_info)

                if plans := bag.plans.all():
                    for plan in plans:
                        actions.grant_student_capabilities(
                            request.user, plan, selected_cohort=request.GET.get("selected_cohort")
                        )

                has_referral_coupons = False
                if invoice.status == Invoice.Status.FULFILLED and invoice.amount > 0:
                    has_referral_coupons = coupons.exclude(referral_type="NO_REFERRAL").exists()

                if has_referral_coupons:
                    transaction.on_commit(lambda inv_id=invoice.id: register_referral_from_invoice.delay(inv_id))

                serializer = GetInvoiceSerializer(invoice, many=False)

                tasks_activity.add_activity.delay(
                    request.user.id,
                    "checkout_completed",
                    related_type="payments.Invoice",
                    related_id=serializer.instance.id,
                )

                data = serializer.data
                serializer = GetCouponSerializer(coupons, many=True)
                data["coupons"] = serializer.data

                return Response(data, status=201)

            except Exception as e:
                transaction.savepoint_rollback(sid)
                raise e


class AcademyPlanSubscriptionView(APIView):

    extensions = APIViewExtensions(sort="-id", paginate=True)

    @capable_of("crud_subscription")
    def post(self, request, plan_slug: str, academy_id: int):
        lang = get_user_language(request)
        proof = actions.validate_and_create_proof_of_payment(request, request.user, academy_id, lang)

        request.data["plans"] = [plan_slug]

        try:
            invoice, coupons = actions.validate_and_create_subscriptions(request, request.user, proof, academy_id, lang)

        except Exception as e:
            proof.delete()
            raise e

        s1 = GetInvoiceSerializer(invoice, many=False)
        s2 = GetCouponSerializer(coupons, many=True)

        data = s1.data
        data["coupons"] = s2.data

        return Response(data)


class PaymentMethodView(APIView):
    extensions = APIViewExtensions(sort="-id", paginate=True)
    permission_classes = [AllowAny]

    def get(self, request):
        handler = self.extensions(request)
        lang = get_user_language(request)

        # Define the custom filter function for country_code
        def country_code_filter(value: str):
            if not value:
                return Q()
            return Q(included_country_codes__exact="") | Q(included_country_codes__icontains=value)

        query = handler.lookup.build(
            lang,
            strings={
                "exact": [
                    "currency_code",
                    "lang",
                    "academy_id",
                    "visibility",
                ],
            },
            # Use the custom field handler
            custom_fields={"country_code": country_code_filter},
        )

        items = PaymentMethod.objects.filter(query)

        items = handler.queryset(items)
        serializer = GetPaymentMethod(items, many=True)

        return handler.response(serializer.data)


class AcademyPaymentMethodView(APIView):
    extensions = APIViewExtensions(sort="-id", paginate=True)

    @capable_of("read_paymentmethod")
    def get(self, request, paymentmethod_id=None, academy_id=None):
        """
        Get payment methods for the academy.
        Returns both academy-specific and global payment methods (where academy=null).
        """
        handler = self.extensions(request)
        lang = get_user_language(request)

        if paymentmethod_id:
            # Get specific payment method
            method = PaymentMethod.objects.filter(
                Q(academy__id=academy_id) | Q(academy__isnull=True), id=paymentmethod_id
            ).first()

            if not method:
                raise ValidationException(
                    translation(
                        lang,
                        en="Payment method not found",
                        es="Método de pago no encontrado",
                        slug="payment-method-not-found",
                    ),
                    code=404,
                )

            serializer = GetPaymentMethod(method, many=False)
            return Response(serializer.data)

        # List payment methods for this academy and global ones
        items = PaymentMethod.objects.filter(Q(academy__id=academy_id) | Q(academy__isnull=True))

        # Optional filters
        visibility = request.GET.get("visibility")
        if visibility:
            items = items.filter(visibility=visibility)

        currency_code = request.GET.get("currency_code")
        if currency_code:
            items = items.filter(currency__code__iexact=currency_code)

        lang_filter = request.GET.get("lang")
        if lang_filter:
            items = items.filter(lang=lang_filter)

        deprecated = request.GET.get("deprecated")
        if deprecated is not None:
            items = items.filter(deprecated=deprecated.lower() in ["true", "1", "yes"])

        items = handler.queryset(items)
        serializer = GetPaymentMethod(items, many=True)

        return handler.response(serializer.data)

    @capable_of("crud_paymentmethod")
    def post(self, request, academy_id):
        academy = Academy.objects.filter(id=academy_id).first()

        serializer = PaymentMethodSerializer(data={**request.data, "academy": academy.id})
        if serializer.is_valid():
            serializer.save(academy=academy)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of("crud_paymentmethod")
    def put(self, request, academy_id, paymentmethod_id):
        lang = get_user_language(request)
        method = PaymentMethod.objects.filter(id=paymentmethod_id, academy__id=academy_id).first()
        if not method:
            raise ValidationException(
                translation(
                    lang,
                    en="Payment method not found for this academy",
                    es="Método de pago no encontrado para esta academia",
                    slug="payment-method-not-found",
                ),
                code=404,
            )

        serializer = PaymentMethodSerializer(method, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of("crud_paymentmethod")
    def delete(self, request, academy_id, paymentmethod_id):
        lang = get_user_language(request)
        method = PaymentMethod.objects.filter(id=paymentmethod_id, academy__id=academy_id).first()
        if not method:
            raise ValidationException(
                translation(
                    lang,
                    en="Payment method not found for this academy",
                    es="Método de pago no encontrado para esta academia",
                    slug="payment-method-not-found",
                ),
                code=404,
            )

        method.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AcademyPlanServiceItemView(APIView):
    extensions = APIViewExtensions(sort="-id", paginate=True)

    @capable_of("crud_plan")
    def post(self, request, academy_id=None):
        logger.info(f"AcademyPlanServiceItemView.post called by user {request.user.id}")
        lang = get_user_language(request)
        handler = self.extensions(request)

        try:
            request_data = request.data
        except Exception as e:
            raise ValidationException(
                translation(
                    lang,
                    en=f"Invalid JSON format: {str(e)}",
                    es=f"Formato JSON inválido: {str(e)}",
                    slug="invalid-json-format",
                ),
                code=400,
            )

        plan = request_data.get("plan")
        if not plan:
            raise ValidationException(
                translation(
                    lang,
                    en="plan is required",
                    es="plan es requerido",
                    slug="plan-required",
                ),
                code=400,
            )

        plan_kwargs = {}
        if plan and isinstance(plan, int):
            plan_kwargs["id"] = plan
        elif plan and isinstance(plan, str):
            plan_kwargs["slug"] = plan

        plan = Plan.objects.filter(**plan_kwargs).first()

        if not plan:
            raise ValidationException(
                translation(
                    lang,
                    en="Plan not found",
                    es="Plan no encontrado",
                    slug="plan-not-found",
                ),
                code=404,
            )

        service_item = request_data.get("service_item")
        if not service_item:
            raise ValidationException(
                translation(
                    lang,
                    en="service_item_id(s) is required",
                    es="service_item_id(s) es requerido",
                    slug="service-item-required",
                ),
                code=400,
            )

        # Handle different input formats for service_item
        if isinstance(service_item, int):
            service_item_ids = [service_item]
        elif isinstance(service_item, str):
            if "," in service_item:
                service_item_ids = [int(x.strip()) for x in service_item.split(",") if x.strip().isdigit()]
            else:
                service_item_ids = [int(service_item)]
        elif isinstance(service_item, list):
            # Validate that list doesn't contain null values
            if None in service_item or any(x is None for x in service_item):
                raise ValidationException(
                    translation(
                        lang,
                        en="service_item array cannot contain null values. Use an empty array [] or omit the field if you don't want to add service items.",
                        es="El array service_item no puede contener valores null. Use un array vacío [] u omita el campo si no desea agregar service items.",
                        slug="service-item-contains-null",
                    ),
                    code=400,
                )

            # Validate that all items are valid integers
            service_item_ids = []
            for x in service_item:
                try:
                    service_item_ids.append(int(x))
                except (ValueError, TypeError):
                    raise ValidationException(
                        translation(
                            lang,
                            en=f"Invalid service_item value: {x}. All values must be valid integers.",
                            es=f"Valor service_item inválido: {x}. Todos los valores deben ser enteros válidos.",
                            slug="invalid-service-item-value",
                        ),
                        code=400,
                    )
        else:
            raise ValidationException(
                translation(
                    lang,
                    en="service_item must be an integer, string, or list",
                    es="service_item debe ser un entero, cadena o lista",
                    slug="invalid-service-item-format",
                ),
                code=400,
            )

        service_items = ServiceItem.objects.filter(id__in=service_item_ids)
        if len(service_items) != len(service_item_ids):
            found_ids = [item.id for item in service_items]
            missing_ids = [id for id in service_item_ids if id not in found_ids]
            raise ValidationException(
                translation(
                    lang,
                    en=f"Service items not found: {missing_ids}",
                    es=f"Service items no encontrados: {missing_ids}",
                    slug="service-item-not-found",
                ),
                code=404,
            )

        created_items = []
        for service_item in service_items:
            psi, created = PlanServiceItem.objects.get_or_create(plan=plan, service_item=service_item)
            created_items.append(
                {"plan_service_item_id": psi.id, "service_item_id": service_item.id, "created": created}
            )

        return handler.response(
            {
                "status": "ok",
                "created_items": created_items,
                "total_created": len([item for item in created_items if item["created"]]),
            }
        )

    @capable_of("crud_plan")
    def delete(self, request, academy_id=None):
        lang = get_user_language(request)
        handler = self.extensions(request)

        try:
            request_data = request.data
        except Exception as e:
            raise ValidationException(
                translation(
                    lang,
                    en=f"Invalid JSON format: {str(e)}",
                    es=f"Formato JSON inválido: {str(e)}",
                    slug="invalid-json-format",
                ),
                code=400,
            )

        plan_service_item = request_data.get("plan_service_item")
        if not plan_service_item:
            raise ValidationException(
                translation(
                    lang,
                    en="plan_service_item_id(s) is required",
                    es="plan_service_item_id(s) es requerido",
                    slug="plan-service-item-id-required",
                ),
                code=400,
            )

        if isinstance(plan_service_item, int):
            plan_service_item_ids = [plan_service_item]
        elif isinstance(plan_service_item, str):
            if "," in plan_service_item:
                plan_service_item_ids = [int(x.strip()) for x in plan_service_item.split(",") if x.strip().isdigit()]
            else:
                plan_service_item_ids = [int(plan_service_item)]

        plan_service_items = PlanServiceItem.objects.filter(id__in=plan_service_item_ids)
        if len(plan_service_items) != len(plan_service_item_ids):
            found_ids = [item.id for item in plan_service_items]
            missing_ids = [id for id in plan_service_item_ids if id not in found_ids]
            raise ValidationException(
                translation(
                    lang,
                    en=f"Plan service items not found: {missing_ids}",
                    es=f"Plan service items no encontrados: {missing_ids}",
                    slug="plan-service-item-not-found",
                ),
                code=404,
            )

        deleted_count = plan_service_items.count()
        plan_service_items.delete()

        return handler.response(
            {"status": "ok", "deleted": True, "deleted_count": deleted_count, "deleted_ids": plan_service_item_ids}
        )


# ------------------------------
# Team member endpoints (scaffold)
# ------------------------------


class SubscriptionBillingTeamView(APIView):
    """Manage Subscription's billing team (create/update/show)."""

    throttle_classes = [UserRateThrottle, AnonRateThrottle]
    extensions = APIViewExtensions(sort="-id")

    def _serializer(self, team: SubscriptionBillingTeam) -> dict[str, Any]:
        subscription = team.subscription
        period_start, period_end = team.get_current_monthly_period_dates()
        return {
            "id": team.id,
            "subscription": subscription.id,
            "name": team.name,
            "seats_limit": team.seats_limit,
            "additional_seats": team.additional_seats,
            "seats_count": team.seats.filter(is_active=True).count(),
            "seats_log": team.seats_log,
            # Auto-recharge settings
            "auto_recharge_enabled": team.auto_recharge_enabled,
            "recharge_threshold_amount": str(team.recharge_threshold_amount),
            "recharge_amount": str(team.recharge_amount),
            "max_period_spend": str(team.max_period_spend) if team.max_period_spend else None,
            # Current spending (calculated from invoices)
            "current_period_spend": team.get_current_period_spend(),
            # Virtual attributes for current period
            "period_start": period_start.isoformat().replace("+00:00", "T") if period_start else None,
            "period_end": period_end.isoformat().replace("+00:00", "T") if period_end else None,
            # Subscription currency
            "currency": subscription.currency.code if subscription.currency else None,
        }

    def get(self, request, subscription_id: int):
        lang = get_user_language(request)

        subscription = Subscription.objects.filter(id=subscription_id).first()
        if not subscription:
            raise ValidationException(
                translation(
                    lang, en="Subscription not found", es="Suscripción no encontrada", slug="subscription-not-found"
                ),
                code=404,
            )

        if request.user.id != subscription.user_id:
            raise ValidationException(
                translation(
                    lang,
                    en="Only the owner can manage team",
                    es="Solo el dueño puede gestionar el equipo",
                    slug="only-owner-allowed",
                ),
                code=403,
            )

        team = SubscriptionBillingTeam.objects.filter(subscription=subscription).first()
        if not team:
            raise ValidationException(
                translation(
                    lang,
                    en="Billing team not found",
                    es="Equipo de facturación no encontrado",
                    slug="billing-team-not-found",
                ),
                code=404,
            )

        data = self._serializer(team)
        return Response(data, status=status.HTTP_200_OK)

    def put(self, request, subscription_id: int):
        """Update billing team auto-recharge settings."""
        lang = get_user_language(request)

        subscription = Subscription.objects.filter(id=subscription_id).first()
        if not subscription:
            raise ValidationException(
                translation(
                    lang, en="Subscription not found", es="Suscripción no encontrada", slug="subscription-not-found"
                ),
                code=404,
            )

        if request.user.id != subscription.user_id:
            raise ValidationException(
                translation(
                    lang,
                    en="Only the owner can manage team",
                    es="Solo el dueño puede gestionar el equipo",
                    slug="only-owner-allowed",
                ),
                code=403,
            )

        team = SubscriptionBillingTeam.objects.filter(subscription=subscription).first()
        if not team:
            raise ValidationException(
                translation(
                    lang,
                    en="Billing team not found",
                    es="Equipo de facturación no encontrado",
                    slug="billing-team-not-found",
                ),
                code=404,
            )

        # Validate input
        serializer = BillingTeamAutoRechargeSerializer(data=request.data)
        if not serializer.is_valid():
            raise ValidationException(serializer.errors, code=400)

        # Update only the billing-related fields
        update_fields = []
        validated_data = serializer.validated_data

        if "auto_recharge_enabled" in validated_data:
            team.auto_recharge_enabled = validated_data["auto_recharge_enabled"]
            update_fields.append("auto_recharge_enabled")

        if "recharge_threshold_amount" in validated_data:
            team.recharge_threshold_amount = validated_data["recharge_threshold_amount"]
            update_fields.append("recharge_threshold_amount")

        if "recharge_amount" in validated_data:
            team.recharge_amount = validated_data["recharge_amount"]
            update_fields.append("recharge_amount")

        if "max_period_spend" in validated_data:
            team.max_period_spend = validated_data["max_period_spend"]
            update_fields.append("max_period_spend")

        if update_fields:
            team.save(update_fields=update_fields)

        data = self._serializer(team)
        return Response(data, status=status.HTTP_200_OK)


class SubscriptionSeatView(APIView):
    """CRUD for SubscriptionSeat under a subscription's billing team."""

    throttle_classes = [UserRateThrottle, AnonRateThrottle]

    def _get_subscription(self, subscription_id: int, lang: str):
        subscription = Subscription.objects.filter(id=subscription_id).first()
        if not subscription:
            raise ValidationException(
                translation(
                    lang, en="Subscription not found", es="Suscripción no encontrada", slug="subscription-not-found"
                ),
                code=404,
            )

        return subscription

    def _get_plan(self, subscription: Subscription, lang: str):
        plan = subscription.plans.first()
        if not plan:
            raise ValidationException(
                translation(lang, en="Plan not found", es="Plan no encontrado", slug="plan-not-found"),
                code=404,
            )

        if not plan.seat_service_price:
            raise ValidationException(
                translation(
                    lang,
                    en="Plan does not support team",
                    es="Plan no soporta equipo",
                    slug="plan-does-not-support-team-seats",
                ),
                code=400,
            )

        return plan

    def _get_team(self, subscription: Subscription, lang: str):
        team = SubscriptionBillingTeam.objects.filter(subscription=subscription).first()
        if not team:
            raise ValidationException(
                translation(lang, en="Team not found", es="Equipo no encontrado", slug="team-not-found"),
                code=404,
            )
        return team

    def _get_seats(self, team: SubscriptionBillingTeam) -> QuerySet[SubscriptionSeat] | list[SubscriptionSeat]:
        return SubscriptionSeat.objects.filter(billing_team=team)

    # it's using a serializer like this because serpy doesn't support async code
    def _serialize_seat(self, seat: SubscriptionSeat) -> dict[str, Any]:
        return {
            "id": seat.id,
            "email": seat.email,
            "user": seat.user_id,
            "is_active": seat.is_active,
            "seat_log": seat.seat_log,
        }

    def get(self, request, subscription_id: int, seat_id: int = None):
        lang = get_user_language(request)

        subscription = self._get_subscription(subscription_id, lang)
        team = self._get_team(subscription, lang)
        qs = self._get_seats(team)
        if seat_id:
            seat = qs.filter(id=seat_id).first()
            if not seat:
                raise ValidationException(
                    translation(lang, en="Seat not found", es="Asiento no encontrado", slug="seat-not-found"),
                    code=404,
                )
            data = self._serialize_seat(seat)
            return Response(data, status=status.HTTP_200_OK)

        items = [self._serialize_seat(s) for s in qs]
        return Response(items, status=status.HTTP_200_OK)

    def _get_user(self, email: str):
        user = User.objects.filter(email_iexact=email).first()
        return user

    def put(self, request, subscription_id: int):
        lang = get_user_language(request)
        data = request.data or {}

        subscription = self._get_subscription(subscription_id, lang)

        if request.user.id != subscription.user_id:
            raise ValidationException(
                translation(
                    lang,
                    en="Only the owner can manage team members",
                    es="Solo el dueño puede gestionar miembros del equipo",
                    slug="only-owner-allowed",
                ),
                code=403,
            )

        add_seats = actions.normalize_add_seats(data.get("add_seats", []))
        replace_seats = actions.normalize_replace_seat(data.get("replace_seats", []))

        if not add_seats and not replace_seats:
            raise ValidationException(
                translation(
                    lang,
                    en="Add seats or replace seats are required",
                    es="Agregar asientos o reemplazar asientos son requeridos",
                    slug="add-or-replace-seats-required",
                ),
                code=400,
            )

        subscription = self._get_subscription(subscription_id, lang)
        team = self._get_team(subscription, lang)

        actions.validate_seats_limit(team, add_seats, replace_seats, lang)

        result: list[SubscriptionSeat] = []
        errors: list[ValidationException] = []

        for seat in add_seats:
            try:
                result.append(actions.create_seat(seat["email"], seat["user"], team, lang))
            except ValidationException as e:
                errors.append(e)

        for seat in replace_seats:
            try:
                s = SubscriptionSeat.objects.filter(billing_team=team, email=seat["from_email"]).first()
                if not s:
                    raise ValidationException(
                        translation(
                            lang,
                            en="Seat not found",
                            es="Asiento no encontrado",
                            slug="seat-not-found",
                        ),
                        code=404,
                    )
                u = None
                if seat["to_user"]:
                    u = User.objects.filter(id=seat["to_user"]).first()
                    if not u:
                        raise ValidationException(
                            translation(
                                lang,
                                en="User not found",
                                es="Usuario no encontrado",
                                slug="user-not-found",
                            ),
                            code=404,
                        )

                elif seat["to_email"]:
                    u = User.objects.filter(email=seat["to_email"]).first()

                result.append(actions.replace_seat(seat["from_email"], seat["to_email"], u, s, lang))
            except ValidationException as e:
                errors.append(e)

        return Response(
            {
                "data": [self._serialize_seat(seat) for seat in result],
                "errors": [
                    {
                        "message": getattr(e, "detail", str(e)),
                        "code": getattr(e, "code", 400),
                    }
                    for e in errors
                ],
            },
            status=status.HTTP_207_MULTI_STATUS,
        )

    def delete(self, request, subscription_id: int, seat_id: int):
        lang = get_user_language(request)
        subscription = self._get_subscription(subscription_id, lang)

        if request.user.id != subscription.user_id:
            raise ValidationException(
                translation(
                    lang,
                    en="Only the owner can manage team members",
                    es="Solo el dueño puede gestionar miembros del equipo",
                    slug="only-owner-allowed",
                ),
                code=403,
            )

        seat = SubscriptionSeat.objects.filter(
            billing_team__subscription=subscription, id=seat_id, is_active=True
        ).first()
        if not seat:
            raise ValidationException(
                translation(lang, en="Seat not found", es="Asiento no encontrado", slug="seat-not-found"), code=404
            )
        seat.user = None
        seat.is_active = False
        seat.save(update_fields=["is_active", "user"])

        Consumable.objects.filter(subscription_seat_id=seat.id).update(user=None)

        return Response(status=status.HTTP_204_NO_CONTENT)
