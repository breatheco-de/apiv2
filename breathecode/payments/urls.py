from django.contrib import admin
from django.urls import include, path

from .views import PlanView, CreditView, ServiceView, ServiceItemView

app_name = 'notify'
urlpatterns = [
    # path('plan', PlanView.as_view()),
    # path('plan/<slug:plan_slug>', PlanView.as_view()),
    # path('plan/<slug:plan_slug>/services', ServiceView.as_view()),
    path('service', ServiceView.as_view()),
    path('service/<slug:service_slug>', ServiceView.as_view()),
    # path('service/<slug:service_slug>/plans', PlanView.as_view()),
    # path('subscription', PlanView.as_view()),
    # path('subscription/<slug:plan_slug>', PlanView.as_view()),
    # path('subscription/<slug:plan_slug>/services', ServiceView.as_view()),
    path('credit', CreditView.as_view()),
    path('credit/<slug:service_slug>', CreditView.as_view()),
    path('credit/<int:invoice_id>', CreditView.as_view()),
    # path('credit/<slug:plan_slug>/services', ServiceView.as_view()),
    # path('credit/<slug:plan_slug>/service_slug/item', ServiceItemView.as_view()),
]
