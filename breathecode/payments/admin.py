from django.contrib import admin

from breathecode.payments.models import (Bag, Consumable, Currency, FinancialReputation,
                                         PaymentServiceScheduler, Invoice, PaymentContact, Plan,
                                         PlanTranslation, Service, ServiceItem, ServiceStockScheduler,
                                         ServiceTranslation, Subscription)

# Register your models here.


@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ('id', 'code', 'name')
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


@admin.register(PaymentServiceScheduler)
class PaymentServiceSchedulerAdmin(admin.ModelAdmin):
    list_display = ('id', 'academy', 'service', 'cohort_pattern', 'renew_every', 'renew_every_unit')
    list_filter = ['academy', 'renew_every_unit']
    search_fields = [
        'service__slug', 'service__title', 'service__groups__name', 'service__cohorts__slug',
        'service__mentorship_services__slug'
    ]


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ('id', 'slug', 'status', 'trial_duration', 'trial_duration_unit', 'owner')
    list_filter = ['trial_duration_unit', 'owner']
    search_fields = ['lang', 'title']


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


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'amount', 'currency', 'paid_at', 'status', 'stripe_id', 'user', 'academy')
    list_filter = ['status', 'academy']


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'paid_at', 'status', 'is_refundable', 'valid_until', 'pay_every', 'pay_every_unit',
                    'user')
    list_filter = ['status', 'is_refundable', 'pay_every_unit']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']


@admin.register(ServiceStockScheduler)
class ServiceStockSchedulerAdmin(admin.ModelAdmin):
    list_display = ('id', 'subscription', 'service_item', 'plan_financing', 'last_renew')

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


@admin.register(FinancialReputation)
class FinancialReputationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'in_4geeks', 'in_stripe')
    list_filter = ['in_4geeks', 'in_stripe']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']


@admin.register(Bag)
class BagAdmin(admin.ModelAdmin):
    list_display = ('id', 'status', 'type', 'chosen_period', 'academy', 'user', 'is_recurrent',
                    'was_delivered')
    list_filter = ['status', 'type', 'chosen_period', 'academy', 'is_recurrent']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
