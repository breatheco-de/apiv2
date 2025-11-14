from django import forms
from django.contrib import admin
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.html import format_html

from breathecode.payments import signals, tasks
from breathecode.payments.models import (
    AcademyPaymentSettings,
    AcademyService,
    Bag,
    CohortSet,
    CohortSetCohort,
    CohortSetTranslation,
    Consumable,
    ConsumptionSession,
    Coupon,
    Currency,
    EventTypeSet,
    EventTypeSetTranslation,
    FinancialReputation,
    FinancingOption,
    Invoice,
    MentorshipServiceSet,
    MentorshipServiceSetTranslation,
    PaymentContact,
    PaymentMethod,
    Plan,
    PlanFinancing,
    PlanFinancingSeat,
    PlanFinancingTeam,
    PlanOffer,
    PlanOfferTranslation,
    PlanServiceItem,
    PlanServiceItemHandler,
    PlanTranslation,
    ProofOfPayment,
    Seller,
    Service,
    ServiceItem,
    ServiceItemFeature,
    ServiceStockScheduler,
    ServiceTranslation,
    Subscription,
    SubscriptionBillingTeam,
    SubscriptionSeat,
    SubscriptionServiceItem,
)

# Register your models here.


@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name", "decimals")
    search_fields = ["code", "code"]


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("id", "slug", "type", "consumer", "owner", "private")
    list_filter = ["owner", "type", "consumer", "private"]
    search_fields = ["slug", "title", "groups__name"]


@admin.register(ServiceTranslation)
class ServiceTranslationAdmin(admin.ModelAdmin):
    list_display = ("id", "lang", "title", "description", "service")
    list_filter = ["service__owner", "lang"]
    search_fields = ["service__slug", "title", "service__groups__name"]


@admin.register(ServiceItem)
class ServiceItemAdmin(admin.ModelAdmin):
    list_display = ("id", "unit_type", "how_many", "is_team_allowed", "service")
    list_filter = ["service__owner", "is_team_allowed"]
    search_fields = [
        "service__slug",
        "service__title",
        "service__groups__name",
    ]


@admin.register(ServiceItemFeature)
class ServiceItemFeatureAdmin(admin.ModelAdmin):
    list_display = ("id", "service_item", "lang", "one_line_desc")
    list_filter = ["service_item__service__owner", "lang"]
    search_fields = [
        "service_item__service__slug",
        "service_item__service__title",
        "service_item__service__groups__name",
    ]


@admin.register(FinancingOption)
class FinancingOptionAdmin(admin.ModelAdmin):
    list_display = ("id", "monthly_price", "currency", "how_many_months")
    list_filter = ["currency__code"]


class PlanServiceItemInline(admin.TabularInline):
    model = PlanServiceItem
    extra = 0
    autocomplete_fields = ("service_item",)


class PlanTranslationInline(admin.StackedInline):
    model = PlanTranslation
    extra = 0


class PlanOfferInline(admin.StackedInline):
    model = PlanOffer
    fk_name = "original_plan"
    extra = 0


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "slug",
        "status",
        "is_renewable",
        "consumption_strategy",
        "is_onboarding",
        "has_waiting_list",
        "trial_duration",
        "trial_duration_unit",
        "owner",
        "exclude_from_referral_program",
    )
    list_filter = [
        "status",
        "is_renewable",
        "consumption_strategy",
        "is_onboarding",
        "has_waiting_list",
        "exclude_from_referral_program",
        "trial_duration_unit",
        "time_of_life_unit",
        "owner",
    ]
    search_fields = ["slug", "title"]
    raw_id_fields = [
        "owner",
        "invites",
        "seat_service_price",
        "cohort_set",
        "mentorship_service_set",
        "event_type_set",
    ]
    filter_horizontal = ("financing_options", "add_ons")
    list_select_related = ("owner",)

    fieldsets = (
        (
            "Basic",
            {
                "fields": (
                    "slug",
                    "title",
                    "status",
                    "owner",
                    "is_onboarding",
                    "has_waiting_list",
                    "exclude_from_referral_program",
                )
            },
        ),
        (
            "Renewal & Lifetime",
            {
                "fields": (
                    "is_renewable",
                    "trial_duration",
                    "trial_duration_unit",
                    "time_of_life",
                    "time_of_life_unit",
                )
            },
        ),
        (
            "Pricing",
            {
                "fields": (
                    "currency",
                    "price_per_month",
                    "price_per_quarter",
                    "price_per_half",
                    "price_per_year",
                    "seat_service_price",
                )
            },
        ),
        (
            "Consumption",
            {"fields": ("consumption_strategy",)},
        ),
        (
            "Bundles & Sets",
            {
                "fields": (
                    "cohort_set",
                    "mentorship_service_set",
                    "event_type_set",
                )
            },
        ),
        (
            "Relations",
            {
                "fields": (
                    "financing_options",
                    "add_ons",
                    "invites",
                )
            },
        ),
        (
            "Advanced",
            {
                "classes": ("collapse",),
                "fields": ("pricing_ratio_exceptions",),
            },
        ),
    )

    inlines = [PlanServiceItemInline, PlanTranslationInline, PlanOfferInline]


@admin.register(PlanTranslation)
class PlanTranslationAdmin(admin.ModelAdmin):
    list_display = ("id", "lang", "title", "description", "plan")
    list_filter = ["plan__owner", "lang"]
    search_fields = ["title", "plan__slug"]


def grant_service_permissions(modeladmin, request, queryset):
    for item in queryset.all():
        signals.grant_service_permissions.send_robust(instance=item, sender=item.__class__)


@admin.register(Consumable)
class ConsumableAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "unit_type",
        "how_many",
        "service_item",
        "plan_financing_team",
        "plan_financing_seat",
        "user",
        "subscription",
        "plan_financing",
        "valid_until",
    )
    list_filter = ["unit_type", "service_item__service__slug"]
    search_fields = [
        "service_item__service__slug",
        "user__email",
        "subscription__user__email",
        "plan_financing__user__email",
        "plan_financing_team__financing__user__email",
        "plan_financing_seat__email",
    ]
    raw_id_fields = [
        "user",
        "service_item",
        "cohort_set",
        "event_type_set",
        "mentorship_service_set",
        "subscription_billing_team",
        "subscription_seat",
        "plan_financing_team",
        "plan_financing_seat",
    ]
    actions = [grant_service_permissions]

    def plan_financing_team(self, obj):
        return getattr(obj, "plan_financing_team", None)

    def plan_financing_seat(self, obj):
        return getattr(obj, "plan_financing_seat", None)


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("id", "amount", "currency", "paid_at", "status", "stripe_id", "user", "academy")
    list_filter = ["status", "academy"]
    search_fields = ["id", "status", "user__email"]
    raw_id_fields = ["user", "currency", "bag", "academy"]


def renew_subscription_consumables(modeladmin, request, queryset):
    for item in queryset.all():
        tasks.renew_subscription_consumables.delay(item.id)


def charge_subscription(modeladmin, request, queryset):
    for item in queryset.all():
        tasks.charge_subscription.delay(item.id)


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "paid_at",
        "status",
        "is_refundable",
        "next_payment_at",
        "pay_every",
        "pay_every_unit",
        "user",
    )
    list_filter = ["status", "is_refundable", "pay_every_unit"]
    search_fields = ["user__email", "user__first_name", "user__last_name"]
    raw_id_fields = [
        "user",
        "academy",
        "selected_cohort_set",
        "selected_mentorship_service_set",
        "selected_event_type_set",
        "joined_cohorts",
        "plans",
        "invoices",
        "coupons",
    ]
    actions = [renew_subscription_consumables, charge_subscription]


@admin.register(SubscriptionServiceItem)
class SubscriptionServiceItemAdmin(admin.ModelAdmin):
    list_display = ("id", "subscription", "service_item")
    list_filter = ["subscription__user__email", "subscription__user__first_name", "subscription__user__last_name"]


@admin.register(SubscriptionSeat)
class SubscriptionSeatAdmin(admin.ModelAdmin):
    list_display = ("id", "billing_team", "email", "user")
    list_filter = [
        "billing_team__subscription__user__email",
        "billing_team__subscription__user__first_name",
        "billing_team__subscription__user__last_name",
    ]
    search_fields = [
        "billing_team__subscription__id",
        "email",
        "user__email",
    ]
    raw_id_fields = ["billing_team", "user"]


# SubscriptionSeatInvite is deprecated in favor of pending SubscriptionSeat (email-only)


@admin.register(SubscriptionBillingTeam)
class SubscriptionBillingTeamAdmin(admin.ModelAdmin):
    list_display = ("id", "subscription", "name")
    search_fields = ["subscription__id", "name"]


# BillingTeamMembership removed; managed via SubscriptionSeat


def renew_plan_financing_consumables(modeladmin, request, queryset):
    for item in queryset.all():
        tasks.renew_plan_financing_consumables.delay(item.id)


def charge_plan_financing(modeladmin, request, queryset):
    for item in queryset.all():
        tasks.charge_plan_financing.delay(item.id)


def regenerate_service_stock_schedulers(modeladmin, request, queryset):
    for item in queryset.all():
        tasks.build_service_stock_scheduler_from_plan_financing.delay(item.id)


@admin.register(PlanFinancing)
class PlanFinancingAdmin(admin.ModelAdmin):
    list_display = ("id", "next_payment_at", "valid_until", "status", "user")
    list_filter = ["status"]
    search_fields = ["user__email", "user__first_name", "user__last_name"]
    raw_id_fields = [
        "user",
        "academy",
        "selected_cohort_set",
        "selected_mentorship_service_set",
        "selected_event_type_set",
    ]
    actions = [renew_plan_financing_consumables, charge_plan_financing, regenerate_service_stock_schedulers]


@admin.register(PlanFinancingTeam)
class PlanFinancingTeamAdmin(admin.ModelAdmin):
    list_display = ("id", "financing", "name", "additional_seats", "consumption_strategy", "seats_count")
    list_filter = ["consumption_strategy", "financing__status"]
    search_fields = [
        "name",
        "financing__id",
        "financing__user__email",
        "financing__user__first_name",
        "financing__user__last_name",
    ]
    raw_id_fields = ["financing"]

    def seats_count(self, obj):
        return obj.seats.filter(is_active=True).count()

    seats_count.short_description = "Active seats"


@admin.register(PlanFinancingSeat)
class PlanFinancingSeatAdmin(admin.ModelAdmin):
    list_display = ("id", "team", "email", "user", "is_active", "created_at", "updated_at")
    list_filter = ["is_active", "team__consumption_strategy"]
    search_fields = [
        "email",
        "user__email",
        "user__first_name",
        "user__last_name",
        "team__financing__user__email",
    ]
    raw_id_fields = ["team", "user"]


def add_cohort_set_to_the_subscriptions(modeladmin, request, queryset):
    if queryset.count() > 1:
        raise forms.ValidationError("You just can select one subscription at a time")

    cohort_set_id = queryset.values_list("id", flat=True).first()
    if not cohort_set_id:
        return

    subscriptions = Subscription.objects.filter(
        Q(valid_until__isnull=True) | Q(valid_until__gt=timezone.now()), selected_cohort_set=None
    ).exclude(status__in=["CANCELLED", "DEPRECATED"])

    for item in subscriptions:
        tasks.add_cohort_set_to_subscription.delay(item.id, cohort_set_id)


@admin.register(CohortSet)
class CohortSetAdmin(admin.ModelAdmin):
    list_display = ("id", "slug", "academy")
    list_filter = ["academy__slug"]
    search_fields = ["slug", "academy__slug", "academy__name"]
    actions = [add_cohort_set_to_the_subscriptions]

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "cohorts":
            kwargs["widget"] = admin.widgets.FilteredSelectMultiple(db_field.verbose_name, False)
        return super().formfield_for_manytomany(db_field, request, **kwargs)


@admin.register(CohortSetTranslation)
class CohortSetTranslationAdmin(admin.ModelAdmin):
    list_display = ("id", "cohort_set", "lang", "title", "description", "short_description")
    list_filter = ["lang"]
    search_fields = ["cohort_set__slug", "cohort_set__academy__slug", "cohort_set__academy__name"]


@admin.register(MentorshipServiceSet)
class MentorshipServiceSetAdmin(admin.ModelAdmin):
    list_display = ("id", "slug", "academy")
    list_filter = ["academy__slug"]
    search_fields = ["slug", "academy__slug", "academy__name"]


@admin.register(CohortSetCohort)
class CohortSetCohortAdmin(admin.ModelAdmin):
    list_display = ("id", "cohort_set", "cohort")
    list_filter = ["cohort_set__academy__slug"]
    search_fields = ["cohort_set__slug", "cohort__slug", "cohort__name"]
    raw_id_fields = ["cohort"]


@admin.register(MentorshipServiceSetTranslation)
class MentorshipServiceSetTranslationAdmin(admin.ModelAdmin):
    list_display = ("id", "mentorship_service_set", "lang", "title", "description", "short_description")
    list_filter = ["lang"]
    search_fields = [
        "mentorship_service_set__slug",
        "mentorship_service_set__academy__slug",
        "mentorship_service_set__academy__name",
    ]


@admin.register(EventTypeSet)
class EventTypeSetAdmin(admin.ModelAdmin):
    list_display = ("id", "slug", "academy")
    list_filter = ["academy__slug"]
    search_fields = ["slug", "academy__slug", "academy__name"]
    raw_id_fields = ["academy"]


@admin.register(EventTypeSetTranslation)
class EventTypeSetTranslationAdmin(admin.ModelAdmin):
    list_display = ("id", "event_type_set", "lang", "title", "description", "short_description")
    list_filter = ["lang"]
    search_fields = ["event_type_set__slug", "event_type_set__academy__slug", "event_type_set__academy__name"]
    raw_id_fields = ["event_type_set"]


@admin.register(PlanServiceItem)
class PlanServiceItemAdmin(admin.ModelAdmin):
    list_display = ("id", "plan", "service_item")
    list_filter = ["plan__slug", "plan__owner__slug"]
    raw_id_fields = ["service_item"]
    search_fields = ["plan__slug", "service_item__service__slug"]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "plan":
            kwargs["queryset"] = Plan.objects.select_related().order_by("slug")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(PlanServiceItemHandler)
class PlanServiceItemHandlerAdmin(admin.ModelAdmin):
    list_display = ("id", "handler", "subscription", "plan_financing")


def renew_consumables(modeladmin, request, queryset):
    for item in queryset.all():
        tasks.renew_consumables.delay(item.id)


@admin.register(ServiceStockScheduler)
class ServiceStockSchedulerAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "subscription",
        "plan_financing",
        "service_type",
        "plan_financing_team",
        "plan_financing_seat",
        "subscription_billing_team",
        "subscription_seat",
        "consumables_count",
        "valid_until",
    )
    list_filter = [
        "valid_until",
        "subscription_billing_team",
        "subscription_seat",
        "plan_financing_team",
        "plan_financing_seat",
        "subscription_handler__subscription__status",
        "plan_handler__subscription__status",
        "plan_handler__plan_financing__status",
    ]
    search_fields = [
        "subscription_handler__subscription__id",
        "subscription_handler__subscription__user__email",
        "subscription_handler__subscription__user__first_name",
        "subscription_handler__subscription__user__last_name",
        "plan_handler__subscription__id",
        "plan_handler__subscription__user__email",
        "plan_handler__subscription__user__first_name",
        "plan_handler__subscription__user__last_name",
        "plan_handler__plan_financing__id",
        "plan_handler__plan_financing__user__email",
        "plan_handler__plan_financing__user__first_name",
        "plan_handler__plan_financing__user__last_name",
        "subscription_seat__email",
        "subscription_seat__user__email",
        "plan_financing_seat__email",
        "plan_financing_seat__user__email",
        "subscription_billing_team__name",
        "plan_financing_team__name",
    ]
    raw_id_fields = [
        "subscription_handler",
        "plan_handler",
        "subscription_billing_team",
        "subscription_seat",
        "plan_financing_team",
        "plan_financing_seat",
    ]
    # Use autocomplete to avoid loading all consumables in memory and reduce cursor usage
    autocomplete_fields = ("consumables",)
    list_select_related = (
        "subscription_handler__subscription",
        "subscription_handler__subscription__user",
        "subscription_handler__service_item__service",
        "plan_handler__subscription",
        "plan_handler__subscription__user",
        "plan_handler__plan_financing",
        "plan_handler__plan_financing__user",
        "plan_handler__handler__service_item__service",
        "subscription_seat__user",
        "subscription_billing_team",
        "plan_financing_team",
        "plan_financing_seat__user",
    )
    date_hierarchy = "valid_until"
    actions = [renew_consumables]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Annotate consumables count to avoid N+1 and prefetch M2M for detail views
        # NOTE: Avoid prefetch_related("consumables") here to prevent server-side cursor reuse issues
        # in some deployments. The changelist uses the annotated count; the change form will load
        # the M2M widget query separately.
        return qs.annotate(consumables_count=Count("consumables")).select_related(
            "subscription_handler__subscription",
            "subscription_handler__subscription__user",
            "subscription_handler__service_item__service",
            "plan_handler__subscription",
            "plan_handler__subscription__user",
            "plan_handler__plan_financing",
            "plan_handler__plan_financing__user",
            "plan_handler__handler__service_item__service",
            "subscription_seat__user",
            "subscription_billing_team",
            "plan_financing_team",
            "plan_financing_seat__user",
        )

    def subscription(self, obj):
        if obj.subscription_handler:
            return obj.subscription_handler.subscription

        if obj.plan_handler:
            return obj.plan_handler.subscription

    def plan_financing(self, obj):
        if obj.plan_handler:
            return obj.plan_handler.plan_financing

    def service_type(self, obj):
        handler = obj.plan_handler or obj.subscription_handler
        if handler:
            service_item = getattr(handler, "service_item", None)
            if not service_item:
                service_item = getattr(handler, "handler", None)
                service_item = getattr(service_item, "service_item", None)
            if service_item and service_item.service:
                return service_item.service.type
        return "-"

    service_type.short_description = "Service type"

    def consumables_count(self, obj):
        # Use annotated value if available to avoid extra queries
        return getattr(obj, "consumables_count", None) or obj.consumables.count()


@admin.register(PaymentContact)
class PaymentContactAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "stripe_id")
    search_fields = ["user__email", "user__first_name", "user__last_name"]
    raw_id_fields = ["user"]


@admin.register(FinancialReputation)
class FinancialReputationAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "in_4geeks", "in_stripe")
    list_filter = ["in_4geeks", "in_stripe"]
    search_fields = ["user__email", "user__first_name", "user__last_name"]
    raw_id_fields = ["user"]


@admin.register(Bag)
class BagAdmin(admin.ModelAdmin):
    list_display = ("id", "status", "type", "chosen_period", "academy", "user", "is_recurrent", "was_delivered")
    list_filter = ["status", "type", "chosen_period", "academy", "is_recurrent"]
    search_fields = ["user__email", "user__first_name", "user__last_name"]
    raw_id_fields = ["user", "academy"]


class PlanOfferForm(forms.ModelForm):
    class Meta:
        model = PlanOffer
        fields = "__all__"

    pass


@admin.register(PlanOffer)
class PlanOfferAdmin(admin.ModelAdmin):
    form = PlanOfferForm
    list_display = ("id", "original_plan", "suggested_plan", "show_modal", "expires_at")
    list_filter = ["show_modal"]
    search_fields = ["original_plan__slug", "suggested_plan__slug"]
    raw_id_fields = ["original_plan", "suggested_plan"]


@admin.register(PlanOfferTranslation)
class PlanOfferTranslationAdmin(admin.ModelAdmin):
    list_display = ("id", "offer", "lang", "title", "description", "short_description")
    list_filter = ["lang"]
    search_fields = ["title"]
    raw_id_fields = ["offer"]


@admin.register(AcademyService)
class AcademyServiceAdmin(admin.ModelAdmin):
    list_display = ("service", "academy", "price_per_unit", "currency", "bundle_size", "max_amount")
    list_filter = ["academy", "currency"]
    search_fields = ["service"]
    raw_id_fields = ["service", "academy"]


@admin.register(ConsumptionSession)
class ConsumptionSessionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "consumable",
        "eta",
        "duration",
        "how_many",
        "status",
        "was_discounted",
        "path",
        "related_id",
        "related_slug",
    )
    list_filter = ["was_discounted", "status", "duration"]
    search_fields = [
        "user__email",
        "user__id",
        "user__first_name",
        "user__last_name",
        "path",
        "related_slug",
        "related_id",
        "consumable__service_item__service__slug",
    ]
    raw_id_fields = ["user", "consumable"]


@admin.register(Seller)
class SellerAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "user", "is_active")
    list_filter = ["is_active"]
    search_fields = ["name", "user__email", "user__id", "user__first_name", "user__last_name"]
    raw_id_fields = ["user"]


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "slug",
        "discount_type",
        "discount_value",
        "referral_type",
        "referral_value",
        "auto",
        "seller",
        "offered_at",
        "expires_at",
    )
    list_filter = ["discount_type", "referral_type", "auto"]
    search_fields = [
        "slug",
        "seller__name",
        "seller__user__email",
        "seller__user__id",
        "seller__user__first_name",
        "seller__user__last_name",
    ]
    raw_id_fields = ["seller", "allowed_user", "referred_buyer"]


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ("title", "description", "academy", "third_party_link", "lang", "visibility", "deprecated")
    list_filter = ["academy__name", "lang", "visibility", "deprecated"]
    raw_id_fields = ["academy"]
    search_fields = ["title", "academy__name"]


@admin.register(ProofOfPayment)
class ProofOfPaymentAdmin(admin.ModelAdmin):
    list_display = ("reference", "status", "created_by", "open_image")
    search_fields = ["reference"]
    list_filter = ["status"]

    def open_image(self, obj: ProofOfPayment) -> str:
        if not obj.confirmation_image_url:
            return "No image uploaded"

        return format_html(f"<a target='blank' href='{obj.confirmation_image_url}'>link</a>")


@admin.register(AcademyPaymentSettings)
class AcademyPaymentSettingsAdmin(admin.ModelAdmin):
    list_display = ("academy", "created_at")
    search_fields = ["academy__name", "academy__slug"]
