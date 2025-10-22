"""
URL Configuration for Certificate App

This module defines URL patterns following REST conventions with some specific exceptions
for the BreatheCode API v2.

REST Naming Conventions:
========================

1. Resource-based URLs:
   - Use plural nouns for collections: /academy/specialties, /badges
   - Use singular nouns for individual resources: /certificate/<id>

2. HTTP Methods:
   - GET /badge - List all badges
   - POST /badge - Create new badge
   - GET /badge/<id> - Get specific badge
   - PUT/PATCH /badge/<id> - Update specific badge
   - DELETE /badge/<id> - Delete specific badge

3. Nested Resources:
   - /cohort/<id>/student/<id> - Student certificate in a specific cohort
   - /academy/specialty - Academy specialties

4. Actions (Non-REST exceptions):
   - /token/<token>/ - Get certificate by token (GET)
   - /me - Get current user's certificates

5. Special Endpoints:
   - /me - Current user's certificates
   - /academy/* - Academy-specific resources
   - /cohort/* - Cohort-specific resources

6. URL Naming:
   - Use snake_case for URL names: cohort_id_student_id
   - Include resource type and ID when applicable
   - Be descriptive but concise

Examples:
- cohort_id_student_id - Get/update specific student certificate in cohort
- cohort_id - Get/update cohort certificates
- me - Current user's certificates
- root - Academy certificates (root endpoint)
"""

from django.urls import path

from .views import (
    AcademySpecialtiesView,
    BadgesView,
    CertificateAcademyView,
    CertificateCohortView,
    CertificateMeView,
    CertificateView,
    LayoutView,
    get_certificate,
)

app_name = "certificate"
urlpatterns = [
    path("academy/specialty", AcademySpecialtiesView.as_view()),
    path("badge", BadgesView.as_view()),
    path("academy/layout", LayoutView.as_view()),
    path("token/<str:token>/", get_certificate),
    path("cohort/<int:cohort_id>/student/<int:student_id>", CertificateView.as_view(), name="cohort_id_student_id"),
    path("cohort/<int:cohort_id>", CertificateCohortView.as_view(), name="cohort_id"),
    path("", CertificateAcademyView.as_view(), name="root"),
    path("me", CertificateMeView.as_view(), name="me"),
]
