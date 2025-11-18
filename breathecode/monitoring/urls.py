"""
URL Configuration for Monitoring App

This module defines URL patterns following REST conventions with some specific exceptions
for the BreatheCode API v2.

REST Naming Conventions:
========================

1. Resource-based URLs:
   - Use plural nouns for collections: /academy/downloads, /applications
   - Use singular nouns for individual resources: /download/<id>

2. HTTP Methods:
   - GET /academy/download - List all academy downloads
   - POST /academy/download - Create new download
   - GET /academy/download/<id> - Get specific download
   - PUT/PATCH /academy/download/<id> - Update specific download
   - DELETE /academy/download/<id> - Delete specific download

3. Nested Resources:
   - /academy/download/<id>/signed-url - Signed URL for specific download
   - /reposubscription/<id> - Repository subscription management

4. Actions (Non-REST exceptions):
   - /admin/actions - Django admin actions (GET)
   - /github/webhook/<token> - GitHub webhook (POST)
   - /stripe/webhook - Stripe webhook (POST)

5. Special Endpoints:
   - /academy/* - Academy-specific resources
   - /admin/* - Admin-only endpoints
   - /application - Application monitoring
   - /endpoint - Endpoint monitoring
   - /download - Download management
   - /upload - Upload management
   - /reposubscription - Repository subscriptions
   - /github/* - GitHub integration
   - /stripe/* - Stripe integration

6. URL Naming:
   - Use snake_case for URL names: academy_download_id
   - Include resource type and ID when applicable
   - Be descriptive but concise

Examples:
- academy_download_id - Get/update specific academy download
- academy_download_signed_url - Get signed URL for specific download
- stripe_webhook - Stripe webhook endpoint
- admin_actions - Admin actions endpoint
"""

from django.urls import path

from .views import (
    AcademyDownloadSignedUrlView,
    AcademyDownloadView,
    DjangoAdminView,
    RepositorySubscriptionView,
    get_apps,
    get_download,
    get_endpoints,
    get_upload,
    process_github_webhook,
    process_stripe_webhook,
)

app_name = "monitoring"
urlpatterns = [
    path("admin/actions", DjangoAdminView.as_view(), name="admin_actions"),
    path("application", get_apps),
    path("endpoint", get_endpoints),
    path("download", get_download),
    path("download/<int:download_id>", get_download),
    path("academy/download", AcademyDownloadView.as_view(), name="academy_download"),
    path("academy/download/<int:download_id>", AcademyDownloadView.as_view(), name="academy_download_id"),
    path("academy/download/<int:download_id>/signed-url", AcademyDownloadSignedUrlView.as_view(), name="academy_download_signed_url"),
    path("upload", get_upload),
    path("upload/<int:upload_id>", get_upload),
    path("reposubscription", RepositorySubscriptionView.as_view()),
    path("reposubscription/<int:subscription_id>", RepositorySubscriptionView.as_view()),
    path("github/webhook/<str:subscription_token>", process_github_webhook),
    path("stripe/webhook", process_stripe_webhook, name="stripe_webhook"),
]
