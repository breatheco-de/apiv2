"""
URL Configuration for Works App

This module defines URL patterns following REST conventions with some specific exceptions
for the BreatheCode API v2.

REST Naming Conventions:
========================

1. Resource-based URLs:
   - Use plural nouns for collections: /app/users
   - Use singular nouns for individual resources: /generic

2. HTTP Methods:
   - GET /app/user - List all app users
   - POST /app/user - Create new app user
   - GET /app/user/<id> - Get specific app user
   - PUT/PATCH /app/user/<id> - Update specific app user
   - DELETE /app/user/<id> - Delete specific app user

3. Special Endpoints:
   - /app/* - App-specific resources
   - /generic - Generic endpoint

4. URL Naming:
   - Use snake_case for URL names: app_user
   - Include resource type when applicable
   - Be descriptive but concise

Examples:
- app_user - Get/update app users
- generic - Generic endpoint
"""

from django.urls import path

from .views import AppUserView, GenericView

app_name = "works"
urlpatterns = [
    path("app/user", AppUserView.as_view(), name="app_user"),
    path("generic", GenericView.as_view(), name="generic"),
]
