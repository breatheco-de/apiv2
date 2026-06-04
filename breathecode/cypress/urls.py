"""
URL Configuration for Cypress App (Testing Only)

This module defines URL patterns for Cypress testing endpoints.
These endpoints are only available in test environments.

REST Naming Conventions:
========================

1. Resource-based URLs:
   - Use plural nouns for collections: /load/roles
   - Use singular nouns for individual resources: /mixer

2. HTTP Methods:
   - GET /load/roles - Load test roles
   - POST /mixer - Mix test data
   - GET /clean - Clean test data
   - DELETE /clean/<model> - Clean specific model data

3. Actions (Non-REST exceptions):
   - /load/roles - Load roles for testing (GET)
   - /mixer - Mix test data (POST)
   - /clean - Clean all test data (GET)
   - /clean/<model> - Clean specific model data (GET)

4. Special Endpoints:
   - /load/* - Test data loading
   - /mixer - Test data mixing
   - /clean/* - Test data cleanup

5. URL Naming:
   - Use snake_case for URL names: load_roles
   - Include resource type when applicable
   - Be descriptive but concise

Examples:
- load_roles - Load test roles
- mixer - Mix test data
- clean - Clean all test data
- clean_model - Clean specific model data

Note: These endpoints are only available when ALLOW_UNSAFE_CYPRESS_APP is enabled
or in test environments.
"""

from django.urls import path

from .views import CleanView, LoadRolesView, MixerView

app_name = "events"
urlpatterns = [
    path("load/roles", LoadRolesView.as_view(), name="load_roles"),
    path("mixer", MixerView.as_view(), name="mixer"),
    path("clean", CleanView.as_view(), name="clean"),
    path("clean/<str:model_name>", CleanView.as_view(), name="clean_model"),
]
