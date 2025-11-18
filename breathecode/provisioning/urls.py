"""
URL Configuration for Provisioning App

This module defines URL patterns following REST conventions with some specific exceptions
for the BreatheCode API v2.

REST Naming Conventions:
========================

1. Resource-based URLs:
   - Use plural nouns for collections: /academy/bills, /academy/userconsumptions
   - Use singular nouns for individual resources: /bill/<id>

2. HTTP Methods:
   - GET /academy/bill - List all academy bills
   - POST /academy/bill - Create new bill
   - GET /academy/bill/<id> - Get specific bill
   - PUT/PATCH /academy/bill/<id> - Update specific bill
   - DELETE /academy/bill/<id> - Delete specific bill

3. Nested Resources:
   - /academy/<id>/provisioningprofile - Provisioning profile for specific academy
   - /me/container/new - Create new container for current user
   - /me/workspaces - Get current user's workspaces

4. Actions (Non-REST exceptions):
   - /me/container/new - Redirect to new container (GET)
   - /public/container/new - Public container creation (GET)
   - /me/workspaces - Redirect to workspaces (GET)
   - /bill/html - Render all bills as HTML (GET)
   - /bill/<id>/html - Render specific bill as HTML (GET)

5. Special Endpoints:
   - /me/* - Current user's provisioning resources
   - /public/* - Public provisioning endpoints
   - /academy/* - Academy-specific resources
   - /admin/* - Admin-only endpoints
   - /bill/* - Bill management and rendering

6. URL Naming:
   - Use snake_case for URL names: academy_bill_id
   - Include resource type and ID when applicable
   - Be descriptive but concise

Examples:
- academy_bill_id - Get/update specific academy bill
- academy_id_provisioning_profile - Get/update provisioning profile for academy
- bill_html - Render all bills as HTML
- bill_id_html - Render specific bill as HTML
"""

from django.urls import path
from .views import (
    AcademyProvisioningUserConsumptionView,
    AcademyBillView,
    ProvisioningProfileView,
    UploadView,
    redirect_new_container,
    redirect_new_container_public,
    redirect_workspaces,
    render_html_all_bills,
    render_html_bill,
)

app_name = "provisioning"
urlpatterns = [
    path("me/container/new", redirect_new_container),
    path("public/container/new", redirect_new_container_public),
    path("me/workspaces", redirect_workspaces),
    path("admin/upload", UploadView.as_view(), name="admin_upload"),
    path("academy/userconsumption", AcademyProvisioningUserConsumptionView.as_view(), name="academy_userconsumption"),
    path("academy/bill", AcademyBillView.as_view(), name="academy_bill_id"),
    path("academy/bill/<int:bill_id>", AcademyBillView.as_view(), name="academy_bill_id"),
    path(
        "academy/<int:academy_id>/provisioningprofile",
        ProvisioningProfileView.as_view(),
        name="academy_id_provisioning_profile",
    ),
    path("bill/html", render_html_all_bills, name="bill_html"),
    path("bill/<int:id>/html", render_html_bill, name="bill_id_html"),
    # path('academy/me/container', ContainerMeView.as_view()),
    # path('me/container', ContainerMeView.as_view()),
    # path('me/container/<int:container_id>', ContainerMeView.as_view()),
]
