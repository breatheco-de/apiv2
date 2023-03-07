from django.urls import path

from .views import (AcademyPlanCohortView, AcademyPlanView, AcademyPlanView, AcademyServiceView,
                    AcademySubscriptionView, BagView, CardView, CheckingView, MeConsumableView, MeInvoiceView,
                    AcademyInvoiceView, MeSubscriptionCancelView, MeSubscriptionChargeView,
                    MeSubscriptionUpgradeView, PayView, PlanOfferView, PlanView, ServiceItemView, ServiceView,
                    MeSubscriptionView)

# /v1/payment/offer

app_name = 'payments'
urlpatterns = [
    path('planoffer', PlanOfferView.as_view(), name='planoffer'),
    path('plan', PlanView.as_view(), name='plan'),
    path('plan/<slug:plan_slug>', PlanView.as_view()),
    path('academy/plan', AcademyPlanView.as_view()),
    path('academy/plan/<int:plan_id>', AcademyPlanView.as_view()),
    path('academy/plan/<slug:plan_slug>', AcademyPlanView.as_view()),
    path('academy/plan/<int:plan_id>/cohort', AcademyPlanCohortView.as_view()),
    path('academy/plan/<slug:plan_slug>/cohort', AcademyPlanCohortView.as_view()),
    #FIXME
    # path('academy/plan/<slug:plan_slug>/financingoption', AcademyPlanView.as_view()),
    path('service', ServiceView.as_view()),
    path('service/<slug:service_slug>', ServiceView.as_view()),
    path('service/<slug:service_slug>/items', ServiceItemView.as_view()),
    path('academy/service', AcademyServiceView.as_view()),
    path('academy/service/<slug:service_slug>', AcademyServiceView.as_view()),
    path('serviceitem', ServiceItemView.as_view(), name='serviceitem'),
    path('me/service/consumable', MeConsumableView.as_view(), name='me_service_consumable'),
    path('me/subscription', MeSubscriptionView.as_view(), name='me_subscription'),
    path('me/subscription/charge', MeSubscriptionChargeView.as_view(), name='me_subscription_charge'),
    path('me/subscription/<int:subscription_id>/cancel',
         MeSubscriptionCancelView.as_view(),
         name='me_subscription_id_cancel'),
    path('me/subscription/<int:subscription_id>/upgrade/<int:plan_offer_id>',
         MeSubscriptionUpgradeView.as_view(),
         name='me_subscription_id_upgrade_id'),
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
