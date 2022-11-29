from django.urls import path

from .views import (AcademyPlanView, AcademySubscriptionView, BagView, CardView, CheckingView, ConsumableView,
                    InvoiceView, PayView, PlanView, ServiceItemView, ServiceView, SubscriptionView)

app_name = 'payments'
urlpatterns = [
    #TODO generate plans and services from yml
    # create and renew, never delete
    path('plan', PlanView.as_view()),
    path('plan/<slug:plan_slug>', PlanView.as_view()),
    path('academy/plan', AcademyPlanView.as_view()),
    path('academy/plan/<slug:plan_slug>', AcademyPlanView.as_view()),
    path('service', ServiceView.as_view()),
    path('service/<slug:service_slug>', ServiceView.as_view()),
    path('service/<slug:service_slug>/items', ServiceItemView.as_view()),
    path('service/<slug:service_slug>/consumable', ConsumableView.as_view()),
    path('consumable', ConsumableView.as_view()),
    path('subscription', SubscriptionView.as_view()),
    path('subscription/<int:subscription_id>', SubscriptionView.as_view()),
    path('academy/subscription', AcademySubscriptionView.as_view()),
    path('academy/subscription/<int:subscription_id>', AcademySubscriptionView.as_view()),
    # path('credit', CreditView.as_view()),
    # path('credit/<int:credit_id>', CreditView.as_view()),
    path('invoice', InvoiceView.as_view()),
    path('invoice/<int:invoice_id>', InvoiceView.as_view()),
    path('academy/invoice', InvoiceView.as_view()),
    path('academy/invoice/<int:invoice_id>', InvoiceView.as_view()),
    path('card', CardView.as_view()),
    path('bag', BagView.as_view()),
    #TODO: can pass a cohort and if is free trial or not
    path('checking', CheckingView.as_view(), name='checking'),
    path('pay', PayView.as_view(), name='pay'),
]
