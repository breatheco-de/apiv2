from django import forms
from django.contrib import admin
from django.db.models import Q
from django.utils import timezone

from breathecode.payments import signals, tasks
from breathecode.payments.models import (
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
    Plan,
    PlanFinancing,
    PlanOffer,
    PlanOfferTranslation,
    PlanServiceItem,
    PlanServiceItemHandler,
    PlanTranslation,
    Seller,
    Service,
    ServiceItem,
    ServiceItemFeature,
    ServiceSet,
    ServiceSetTranslation,
    ServiceStockScheduler,
    ServiceTranslation,
    Subscription,
    SubscriptionServiceItem,
)

# Register your models here.


@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ('id', 'code', 'name', 'decimals')
    search_fields = ['code', 'code']


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'slug', 'owner', 'private')
    list_filter = ['owner']
    search_fields = ['slug', 'title', 'groups__name']


@admin.register(ServiceTranslation)
class ServiceTranslationAdmin(admin.ModelAdmin):
    list_display = ('id', 'lang', 'title', 'description', 'service')
    list_filter = ['service__owner', 'lang']
    search_fields = ['service__slug', 'title', 'service__groups__name']


@admin.register(ServiceItem)
class ServiceItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'unit_type', 'how_many', 'service')
    list_filter = ['service__owner']
    search_fields = [
        'service__slug', 'service__title', 'service__groups__name', 'service__cohorts__slug',
        'service__mentorship_services__slug'
    ]


@admin.register(ServiceItemFeature)
class ServiceItemFeatureAdmin(admin.ModelAdmin):
    list_display = ('id', 'service_item', 'lang', 'one_line_desc')
    list_filter = ['service_item__service__owner', 'lang']
    search_fields = [
        'service_item__service__slug', 'service_item__service__title', 'service_item__service__groups__name'
    ]


@admin.register(FinancingOption)
class FinancingOptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'monthly_price', 'currency', 'how_many_months')
    list_filter = ['currency__code']


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ('id', 'slug', 'status', 'trial_duration', 'trial_duration_unit', 'owner')
    list_filter = ['trial_duration_unit', 'owner']
    search_fields = ['lang', 'title']
    raw_id_fields = ['owner']
    filter_horizontal = ('invites', )


@admin.register(PlanTranslation)
class PlanTranslationAdmin(admin.ModelAdmin):
    list_display = ('id', 'lang', 'title', 'description', 'plan')
    list_filter = ['plan__owner', 'lang']
    search_fields = ['title', 'plan__slug']


def grant_service_permissions(modeladmin, request, queryset):
    for item in queryset.all():
        signals.grant_service_permissions.send(instance=item, sender=item.__class__)


@admin.register(Consumable)
class ConsumableAdmin(admin.ModelAdmin):
    list_display = ('id', 'unit_type', 'how_many', 'service_item', 'user', 'valid_until')
    list_filter = ['unit_type', 'service_item__service__slug']
    search_fields = ['service_item__service__slug']
    raw_id_fields = ['user', 'service_item', 'cohort_set', 'event_type_set', 'mentorship_service_set']
    actions = [grant_service_permissions]


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'amount', 'currency', 'paid_at', 'status', 'stripe_id', 'user', 'academy')
    list_filter = ['status', 'academy']
    raw_id_fields = ['user', 'currency', 'bag', 'academy']


def renew_subscription_consumables(modeladmin, request, queryset):
    for item in queryset.all():
        tasks.renew_subscription_consumables.delay(item.id)


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'paid_at', 'status', 'is_refundable', 'next_payment_at', 'pay_every', 'pay_every_unit',
                    'user')
    list_filter = ['status', 'is_refundable', 'pay_every_unit']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    raw_id_fields = [
        'user', 'academy', 'selected_cohort_set', 'selected_mentorship_service_set', 'selected_event_type_set'
    ]
    actions = [renew_subscription_consumables]


@admin.register(SubscriptionServiceItem)
class SubscriptionServiceItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'subscription', 'service_item')
    list_filter = ['subscription__user__email', 'subscription__user__first_name', 'subscription__user__last_name']


def renew_plan_financing_consumables(modeladmin, request, queryset):
    for item in queryset.all():
        tasks.renew_plan_financing_consumables.delay(item.id)


@admin.register(PlanFinancing)
class PlanFinancingAdmin(admin.ModelAdmin):
    list_display = ('id', 'next_payment_at', 'valid_until', 'status', 'user')
    list_filter = ['status']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    raw_id_fields = [
        'user', 'academy', 'selected_cohort_set', 'selected_mentorship_service_set', 'selected_event_type_set'
    ]
    actions = [renew_plan_financing_consumables]


def add_cohort_set_to_the_subscriptions(modeladmin, request, queryset):
    if queryset.count() > 1:
        raise forms.ValidationError('You just can select one subscription at a time')

    cohort_set_id = queryset.values_list('id', flat=True).first()
    if not cohort_set_id:
        return

    subscriptions = Subscription.objects.filter(
        Q(valid_until__isnull=True)
        | Q(valid_until__gt=timezone.now()), selected_cohort_set=None).exclude(status__in=['CANCELLED', 'DEPRECATED'])

    for item in subscriptions:
        tasks.add_cohort_set_to_subscription.delay(item.id, cohort_set_id)


@admin.register(CohortSet)
class CohortSetAdmin(admin.ModelAdmin):
    list_display = ('id', 'slug', 'academy')
    list_filter = ['academy__slug']
    search_fields = ['slug', 'academy__slug', 'academy__name']
    actions = [add_cohort_set_to_the_subscriptions]

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == 'cohorts':
            kwargs['widget'] = admin.widgets.FilteredSelectMultiple(db_field.verbose_name, False)
        return super().formfield_for_manytomany(db_field, request, **kwargs)


@admin.register(CohortSetTranslation)
class CohortSetTranslationAdmin(admin.ModelAdmin):
    list_display = ('id', 'cohort_set', 'lang', 'title', 'description', 'short_description')
    list_filter = ['lang']
    search_fields = ['slug', 'academy__slug', 'academy__name']


@admin.register(MentorshipServiceSet)
class MentorshipServiceSetAdmin(admin.ModelAdmin):
    list_display = ('id', 'slug', 'academy')
    list_filter = ['academy__slug']
    search_fields = ['slug', 'academy__slug', 'academy__name']


@admin.register(ServiceSet)
class ServiceSetAdmin(admin.ModelAdmin):
    list_display = ('id', 'slug', 'academy')
    list_filter = ['academy__slug']
    search_fields = ['slug', 'academy__slug', 'academy__name']


@admin.register(CohortSetCohort)
class CohortSetCohortAdmin(admin.ModelAdmin):
    list_display = ('id', 'cohort_set', 'cohort')
    list_filter = ['cohort_set__academy__slug']
    search_fields = ['cohort_set__slug', 'cohort_set__name', 'cohort__slug', 'cohort__name']
    raw_id_fields = ['cohort']


@admin.register(MentorshipServiceSetTranslation)
class MentorshipServiceSetTranslationAdmin(admin.ModelAdmin):
    list_display = ('id', 'mentorship_service_set', 'lang', 'title', 'description', 'short_description')
    list_filter = ['lang']
    search_fields = ['slug', 'academy__slug', 'academy__name']


@admin.register(ServiceSetTranslation)
class ServiceSetTranslationAdmin(admin.ModelAdmin):
    list_display = ('id', 'service_set', 'lang', 'title', 'description', 'short_description')
    list_filter = ['lang']
    search_fields = ['slug', 'academy__slug', 'academy__name']


@admin.register(EventTypeSet)
class EventTypeSetAdmin(admin.ModelAdmin):
    list_display = ('id', 'slug', 'academy')
    list_filter = ['academy__slug']
    search_fields = ['slug', 'academy__slug', 'academy__name']
    raw_id_fields = ['academy']


@admin.register(EventTypeSetTranslation)
class EventTypeSetTranslationAdmin(admin.ModelAdmin):
    list_display = ('id', 'event_type_set', 'lang', 'title', 'description', 'short_description')
    list_filter = ['lang']
    search_fields = ['slug', 'academy__slug', 'academy__name']
    raw_id_fields = ['event_type_set']


@admin.register(PlanServiceItem)
class PlanServiceItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'plan', 'service_item')
    list_filter = ['plan__slug', 'plan__owner__slug']


@admin.register(PlanServiceItemHandler)
class PlanServiceItemHandlerAdmin(admin.ModelAdmin):
    list_display = ('id', 'handler', 'subscription', 'plan_financing')


def renew_consumables(modeladmin, request, queryset):
    for item in queryset.all():
        tasks.renew_consumables.delay(item.id)


@admin.register(ServiceStockScheduler)
class ServiceStockSchedulerAdmin(admin.ModelAdmin):
    list_display = ('id', 'subscription', 'service_item', 'plan_financing', 'valid_until')
    actions = [renew_consumables]

    def subscription(self, obj):
        if obj.subscription_handler:
            return obj.subscription_handler.subscription

        if obj.plan_handler:
            return obj.plan_handler.subscription

    def service_item(self, obj):
        if obj.subscription_handler:
            return obj.subscription_handler.handler.service_item

        if obj.plan_handler:
            return obj.plan_handler.handler.service_item

    def plan_financing(self, obj):
        if obj.plan_handler:
            return obj.plan_handler.plan_financing


@admin.register(PaymentContact)
class PaymentContactAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'stripe_id')
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    raw_id_fields = ['user']


@admin.register(FinancialReputation)
class FinancialReputationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'in_4geeks', 'in_stripe')
    list_filter = ['in_4geeks', 'in_stripe']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    raw_id_fields = ['user']


@admin.register(Bag)
class BagAdmin(admin.ModelAdmin):
    list_display = ('id', 'status', 'type', 'chosen_period', 'academy', 'user', 'is_recurrent', 'was_delivered')
    list_filter = ['status', 'type', 'chosen_period', 'academy', 'is_recurrent']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    raw_id_fields = ['user', 'academy']


@admin.register(PlanOffer)
class PlanOfferAdmin(admin.ModelAdmin):
    list_display = ('id', 'original_plan', 'suggested_plan', 'show_modal', 'expires_at')
    list_filter = ['show_modal']
    search_fields = ['original_plan__slug', 'suggested_plan__slug']
    raw_id_fields = ['original_plan', 'suggested_plan']


@admin.register(PlanOfferTranslation)
class PlanOfferTranslationAdmin(admin.ModelAdmin):
    list_display = ('id', 'offer', 'lang', 'title', 'description', 'short_description')
    list_filter = ['lang']
    search_fields = ['title']
    raw_id_fields = ['offer']


@admin.register(AcademyService)
class AcademyServiceAdmin(admin.ModelAdmin):
    list_display = ('service', 'academy', 'price_per_unit', 'currency', 'bundle_size', 'max_amount')
    list_filter = ['academy', 'currency']
    search_fields = ['service']
    raw_id_fields = ['service', 'academy']


@admin.register(ConsumptionSession)
class ConsumptionSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'consumable', 'eta', 'duration', 'how_many', 'status', 'was_discounted', 'path',
                    'related_id', 'related_slug')
    list_filter = ['was_discounted', 'status', 'duration']
    search_fields = [
        'user__email', 'user__id', 'user__first_name', 'user__last_name', 'path', 'related_slug', 'related_id',
        'consumable__service_item__service__slug'
    ]
    raw_id_fields = ['user', 'consumable']


@admin.register(Seller)
class SellerAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'user', 'is_hidden', 'is_active')
    list_filter = ['is_hidden', 'is_active']
    search_fields = ['name', 'user__email', 'user__id', 'user__first_name', 'user__last_name']
    raw_id_fields = ['user']


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('id', 'slug', 'discount_type', 'discount_value', 'referral_type', 'referral_value', 'auto',
                    'seller', 'offered_at', 'expires_at')
    list_filter = ['discount_type', 'referral_type', 'auto']
    search_fields = [
        'slug', 'seller__name', 'seller__user__email', 'seller__user__id', 'seller__user__first_name',
        'seller__user__last_name'
    ]
    raw_id_fields = ['seller']
