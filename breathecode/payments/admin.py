from django.contrib import admin

from breathecode.payments.models import (Bag, Consumable, Currency, EventTypeSet, EventTypeSetTranslation,
                                         FinancialReputation, FinancingOption, Invoice, MentorshipServiceSet,
                                         MentorshipServiceSetTranslation, PaymentContact, Plan, PlanFinancing,
                                         PlanServiceItem, PlanServiceItemHandler, PlanTranslation, Service,
                                         ServiceItem, ServiceItemFeature, ServiceStockScheduler,
                                         ServiceTranslation, Subscription, SubscriptionServiceItem)

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
        'service_item__service__slug', 'service_item__service__title', 'service_item__service__groups__name',
        'service_item__service__cohorts__slug', 'service_item__service__mentorship_services__slug'
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


@admin.register(PlanTranslation)
class PlanTranslationAdmin(admin.ModelAdmin):
    list_display = ('id', 'lang', 'title', 'description', 'plan')
    list_filter = ['plan__owner', 'lang']
    search_fields = ['title', 'plan__slug']


@admin.register(Consumable)
class ConsumableAdmin(admin.ModelAdmin):
    list_display = ('id', 'unit_type', 'how_many', 'service_item', 'user', 'valid_until')
    list_filter = ['unit_type']
    search_fields = ['service_item__service__slug']
    raw_id_fields = ['user', 'service_item', 'cohort', 'event_type_set', 'mentorship_service_set']


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'amount', 'currency', 'paid_at', 'status', 'stripe_id', 'user', 'academy')
    list_filter = ['status', 'academy']
    raw_id_fields = ['user', 'currency', 'bag', 'academy']


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'paid_at', 'status', 'is_refundable', 'next_payment_at', 'pay_every',
                    'pay_every_unit', 'user')
    list_filter = ['status', 'is_refundable', 'pay_every_unit']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    raw_id_fields = [
        'user', 'academy', 'selected_cohort', 'selected_mentorship_service_set', 'selected_event_type_set'
    ]


@admin.register(SubscriptionServiceItem)
class SubscriptionServiceItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'subscription', 'service_item')
    list_filter = [
        'subscription__user__email', 'subscription__user__first_name', 'subscription__user__last_name'
    ]


@admin.register(PlanFinancing)
class PlanFinancingAdmin(admin.ModelAdmin):
    list_display = ('id', 'next_payment_at', 'valid_until', 'status', 'user')
    list_filter = ['status']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    raw_id_fields = [
        'user', 'academy', 'selected_cohort', 'selected_mentorship_service_set', 'selected_event_type_set'
    ]


@admin.register(MentorshipServiceSet)
class MentorshipServiceSetAdmin(admin.ModelAdmin):
    list_display = ('id', 'slug', 'academy')
    list_filter = ['academy__slug']
    search_fields = ['slug', 'academy__slug', 'academy__name']


@admin.register(MentorshipServiceSetTranslation)
class MentorshipServiceSetTranslationAdmin(admin.ModelAdmin):
    list_display = ('id', 'mentorship_service_set', 'lang', 'title', 'description', 'short_description')
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


@admin.register(ServiceStockScheduler)
class ServiceStockSchedulerAdmin(admin.ModelAdmin):
    list_display = ('id', 'subscription', 'service_item', 'plan_financing', 'valid_until')

    def subscription(self, obj):
        if obj.subscription_handler:
            return obj.subscription_handler.subscription

        if obj.plan_handler:
            return obj.plan_handler.subscription

    def service_item(self, obj):
        if obj.subscription_handler:
            return obj.subscription_handler.service_item

        if obj.plan_handler:
            return obj.plan_handler.service_item

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
    list_display = ('id', 'status', 'type', 'chosen_period', 'academy', 'user', 'is_recurrent',
                    'was_delivered')
    list_filter = ['status', 'type', 'chosen_period', 'academy', 'is_recurrent']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    raw_id_fields = ['user', 'academy']
