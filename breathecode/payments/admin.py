from django.contrib import admin

from breathecode.payments.models import (Bag, Consumable, Credit, Currency, FinancialReputation, Invoice,
                                         PaymentContact, Plan, PlanTranslation, Service, ServiceItem,
                                         Subscription)

# Register your models here.


@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ('id', 'code', 'name')
    # list_filter = ['schedule__name', 'timezone', 'recurrent', 'recurrency_type']
    search_fields = ['code', 'code']


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'slug', 'title', 'description', 'owner', 'private')
    list_filter = ['owner']
    search_fields = ['slug', 'title', 'groups__name', 'cohorts__slug', 'mentorship_services__slug']


# @admin.register(ServiceItem)
# class ServiceItemAdmin(admin.ModelAdmin):
#     list_display = ('id', 'unit_type', 'how_many')
#     list_filter = ['service__academy']
#     search_fields = [
#         'service__slug', 'service__title', 'service__groups__name', 'service__cohorts__slug',
#         'service__mentorship_services__slug'
#     ]


@admin.register(ServiceItem)
class ServiceItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'unit_type', 'how_many', 'service', 'renew_every', 'renew_every_unit')
    list_filter = ['renew_every_unit', 'service__owner']
    search_fields = [
        'service__slug', 'service__title', 'service__groups__name', 'service__cohorts__slug',
        'service__mentorship_services__slug'
    ]


@admin.register(PlanTranslation)
class PlanTranslationAdmin(admin.ModelAdmin):
    list_display = ('id', 'lang', 'title', 'description')
    search_fields = ['lang', 'title']


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ('id', 'slug', 'status', 'renew_every', 'renew_every_unit', 'trial_duration',
                    'trial_duration_unit', 'owner')
    list_filter = ['renew_every_unit', 'trial_duration_unit', 'owner']
    search_fields = ['lang', 'title']


@admin.register(Consumable)
class ConsumableAdmin(admin.ModelAdmin):
    list_display = ('id', 'unit_type', 'how_many', 'service', 'user', 'valid_until')
    list_filter = ['unit_type']
    search_fields = ['service__slug']


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'amount', 'currency', 'paid_at', 'status', 'stripe_id', 'user', 'academy')
    list_filter = ['status', 'academy']


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'paid_at', 'status', 'is_cancellable', 'is_refundable', 'is_auto_renew',
                    'valid_until', 'last_renew', 'renew_credits_at', 'pay_every', 'pay_every_unit',
                    'renew_every', 'renew_every_unit', 'user')
    list_filter = [
        'status', 'is_cancellable', 'is_refundable', 'is_auto_renew', 'pay_every_unit', 'renew_every_unit'
    ]
    search_fields = ['user__email', 'user__first_name', 'user__last_name']


@admin.register(Credit)
class CreditAdmin(admin.ModelAdmin):
    list_display = ('id', 'valid_until', 'is_free_trial', 'invoice')
    list_filter = ['is_free_trial']


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
