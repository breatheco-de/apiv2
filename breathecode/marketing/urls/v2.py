"""
V2 URL Configuration for Marketing App

V2 endpoints use ppc_tracking_id instead of gclid - no backward compatibility.
"""

from django.urls import path

from ..views import (
    create_lead_v2,
    create_lead_captcha_v2,
    create_lead_from_app_v2,
)

app_name = "marketing"
urlpatterns = [
    path("lead", create_lead_v2, name="lead_v2"),
    path("lead-captcha", create_lead_captcha_v2, name="lead_captcha_v2"),
    path("app/<slug:app_slug>/lead", create_lead_from_app_v2, name="app_slug_lead_v2"),
    path("app/lead", create_lead_from_app_v2, name="app_lead_v2"),
]

