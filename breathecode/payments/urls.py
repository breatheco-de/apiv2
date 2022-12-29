from django.urls import path

from .views import (AcademyPlanView, AcademyServiceView, AcademySubscriptionView, BagView, CardView,
                    CheckingView, MeConsumableView, MeInvoiceView, AcademyInvoiceView, PayView, PlanView,
                    ServiceItemView, ServiceView, MeSubscriptionView)

# /v1/payment/offer
# /v1/payment/planoffer?original_plan=<>&from_syllabus=<>

app_name = 'payments'
urlpatterns = [
    #TODO generate plans and services from yml
    # create and renew, never delete
    path('plan', PlanView.as_view()),
    path('plan/<slug:plan_slug>', PlanView.as_view()),
    path('academy/plan', AcademyPlanView.as_view()),
    path('academy/plan/<slug:plan_slug>', AcademyPlanView.as_view()),
    #FIXME
    # path('academy/plan/<slug:plan_slug>/financingoption', AcademyPlanView.as_view()),
    path('service', ServiceView.as_view()),
    path('service/<slug:service_slug>', ServiceView.as_view()),
    path('service/<slug:service_slug>/items', ServiceItemView.as_view()),
    path('academy/service', AcademyServiceView.as_view()),
    path('academy/service/<slug:service_slug>', AcademyServiceView.as_view()),
    path('serviceitem', ServiceItemView.as_view(), name='serviceitem'),
    path('me/service/consumable', MeConsumableView.as_view(), name='me_service_consumable'),
    path('me/subscription', MeSubscriptionView.as_view()),
    path('me/subscription/<int:subscription_id>', MeSubscriptionView.as_view()),
    path('academy/subscription', AcademySubscriptionView.as_view()),
    path('academy/subscription/<int:subscription_id>', AcademySubscriptionView.as_view()),
    path('me/invoice', MeInvoiceView.as_view()),
    path('me/invoice/<int:invoice_id>', MeInvoiceView.as_view()),
    path('academy/invoice', AcademyInvoiceView.as_view()),
    path('academy/invoice/<int:invoice_id>', AcademyInvoiceView.as_view()),
    path('card', CardView.as_view()),
    path('bag', BagView.as_view()),
    path('checking', CheckingView.as_view(), name='checking'),
    path('pay', PayView.as_view(), name='pay'),
]
