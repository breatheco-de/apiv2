from django.contrib import admin
from django.urls import path, include
from .views import PlanView

app_name = 'notify'
urlpatterns = [
    path('plan', PlanView.as_view()),
    path('plan/<slug:plan_slug>', PlanView.as_view()),
    path('plan/<slug:plan_slug>/services', ServiceView.as_view()),
    path('service', ServiceView.as_view()),
    path('service/<slug:service_slug>', ServiceView.as_view()),
    path('service/<slug:service_slug>/plans', PlanView.as_view()),
]
