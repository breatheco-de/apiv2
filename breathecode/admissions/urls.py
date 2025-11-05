"""
URL Configuration for Admissions App

This module defines URL patterns following REST conventions with some specific exceptions
for the BreatheCode API v2.

REST Naming Conventions:
========================

1. Resource-based URLs:
   - Use plural nouns for collections: /academy/cohorts, /syllabus/versions
   - Use singular nouns for individual resources: /academy/cohort/<id>

2. HTTP Methods:
   - GET /academy/cohort - List all cohorts
   - POST /academy/cohort - Create new cohort
   - GET /academy/cohort/<id> - Get specific cohort
   - PUT/PATCH /academy/cohort/<id> - Update specific cohort
   - DELETE /academy/cohort/<id> - Delete specific cohort

3. Nested Resources:
   - /academy/cohort/<id>/user - Users in a specific cohort
   - /academy/cohort/<id>/timeslot - Time slots for a specific cohort

4. Actions (Non-REST exceptions):
   - /academy/cohort/<id>/join - Join a cohort (POST)
   - /academy/cohort/me - Get current user's cohort
   - /academy/activate - Activate academy (POST)

5. Special Endpoints:
   - /me/* - Current user's resources
   - /public/* - Publicly accessible endpoints
   - /academy/* - Academy-only endpoints
   - /admin/* - Admin-only endpoints
   - /catalog/* - Reference data endpoints

6. Deprecated Endpoints:
   - Marked with 🔽 comments for gradual migration
   - Maintained for backward compatibility

7. URL Naming:
   - Use snake_case for URL names: academy_cohort_id
   - Include resource type and ID when applicable
   - Be descriptive but concise

Examples:
- academy_cohort_id - Get/update specific cohort
- academy_cohort_id_user_id - Get/update specific user in cohort
- me_cohort_user_log - Current user's cohort history
- public_cohort_user - Public cohort user data
- admin_cohort - Admin cohort management
"""

from django.urls import path

from .views import (
    AcademyActivateView,
    AcademyCohortHistoryView,
    AcademyCohortTimeSlotView,
    AcademyCohortUserView,
    AcademyCohortView,
    AcademyListView,
    AcademyReportView,
    AcademySyllabusScheduleTimeSlotView,
    AcademySyllabusScheduleView,
    AcademySyncCohortTimeSlotView,
    AcademyTeacherView,
    AcademyView,
    AllSyllabusVersionsView,
    CohortJoinView,
    CohortMeView,
    CohortUserView,
    MeCohortUserHistoryView,
    PublicCohortUserView,
    PublicCohortView,
    SyllabusAssetView,
    SyllabusScheduleView,
    SyllabusVersionCSVView,
    SyllabusVersionForkView,
    SyllabusVersionView,
    SyllabusView,
    UserMeView,
    UserMicroCohortsSyncView,
    UserView,
    get_all_academies,
    get_cities,
    get_countries,
    get_public_syllabus,
    get_schedule,
    get_single_academy,
    get_timezones,
    handle_test_syllabus,
    render_syllabus_preview,
)
from .admin_views import AdminCohortView, AdminStudentView

app_name = "admissions"
urlpatterns = [
    # keep before that academy/cohort/:id
    path("academy/cohort/me", CohortMeView.as_view(), name="academy_cohort_me"),
    path("public/syllabus", get_public_syllabus),
    # deprecated methods, soon to be deleted
    path("cohort/all", PublicCohortView.as_view(), name="cohort_all"),
    path("cohort/user", CohortUserView.as_view(), name="cohort_user"),
    path("cohort/<int:cohort_id>/join", CohortJoinView.as_view(), name="cohort_id_join"),
    path("cohort/<int:cohort_id>/user/<int:user_id>", CohortUserView.as_view(), name="cohort_id_user_id"),
    path("cohort/<int:cohort_id>/user", CohortUserView.as_view(), name="cohort_id_user"),
    # me
    path("me/cohort/user/log", MeCohortUserHistoryView.as_view(), name="me_cohort_user_log"),
    path("me/cohort/<int:cohort_id>/user/log", MeCohortUserHistoryView.as_view(), name="me_cohort_id_user_log"),
    path(
        "me/micro-cohorts/sync/<str:macro_cohort_slug>",
        UserMicroCohortsSyncView.as_view(),
        name="me_micro_cohorts_sync",
    ),
    # new endpoints (replacing above)
    path("academy/cohort/user", AcademyCohortUserView.as_view(), name="academy_cohort_user"),
    path("academy/cohort/<str:cohort_id>/log", AcademyCohortHistoryView.as_view(), name="academy_cohort_id_history"),
    path(
        "academy/cohort/<int:cohort_id>/user/<int:user_id>",
        AcademyCohortUserView.as_view(),
        name="academy_cohort_id_user_id",
    ),
    path("academy/cohort/<int:cohort_id>/user", AcademyCohortUserView.as_view()),
    path(
        "academy/cohort/<int:cohort_id>/timeslot",
        AcademyCohortTimeSlotView.as_view(),
        name="academy_cohort_id_timeslot",
    ),
    path(
        "academy/cohort/<int:cohort_id>/timeslot/<int:timeslot_id>",
        AcademyCohortTimeSlotView.as_view(),
        name="academy_cohort_id_timeslot_id",
    ),
    path("academy/cohort/sync/timeslot", AcademySyncCohortTimeSlotView.as_view(), name="academy_cohort_sync_timeslot"),
    path("academy/cohort/<str:cohort_id>", AcademyCohortView.as_view(), name="academy_cohort_id"),
    # 🔽 this endpoint is deprecated 🔽
    path("academy/certificate/<int:certificate_id>/timeslot", AcademySyllabusScheduleTimeSlotView.as_view()),
    # 🔽 this endpoint is deprecated 🔽
    path(
        "academy/certificate/<int:certificate_id>/timeslot/<int:timeslot_id>",
        AcademySyllabusScheduleTimeSlotView.as_view(),
    ),
    path(
        "academy/schedule/<int:certificate_id>/timeslot",
        AcademySyllabusScheduleTimeSlotView.as_view(),
        name="academy_schedule_id_timeslot",
    ),
    path(
        "academy/schedule/<int:certificate_id>/timeslot/<int:timeslot_id>",
        AcademySyllabusScheduleTimeSlotView.as_view(),
        name="academy_schedule_id_timeslot_id",
    ),
    path("academy/teacher", AcademyTeacherView.as_view(), name="academy_teacher"),
    path("academy", AcademyListView.as_view(), name="academy"),
    path("academy/<int:academy_id>", get_single_academy, name="single_academy"),
    path("academy/me", AcademyView.as_view(), name="academy_me"),
    path("academy/cohort", AcademyCohortView.as_view(), name="academy_cohort"),
    path("academy/activate", AcademyActivateView.as_view(), name="academy_activate"),
    path("user/me", UserMeView.as_view(), name="user_me"),
    path("user", UserView.as_view(), name="user"),
    # 🔽 this endpoint is deprecated 🔽
    path("certificate", SyllabusScheduleView.as_view()),
    # 🔽 this endpoint is deprecated 🔽
    path("certificate/<int:schedule_id>/", get_schedule),
    path("schedule", SyllabusScheduleView.as_view(), name="schedule"),
    path("schedule/<int:schedule_id>/", get_schedule, name="schedule_id"),
    # 🔽 this endpoint is deprecated 🔽
    path("academy/certificate", AcademySyllabusScheduleView.as_view()),
    path("academy/schedule", AcademySyllabusScheduleView.as_view(), name="academy_schedule"),
    path("academy/schedule/<int:certificate_id>", AcademySyllabusScheduleView.as_view(), name="academy_schedule_id"),
    path("syllabus", SyllabusView.as_view(), name="syllabus"),
    path("syllabus/test", handle_test_syllabus),
    path("syllabus/<int:syllabus_id>", SyllabusView.as_view(), name="syllabus_id"),
    path("syllabus/<int:syllabus_id>/version", SyllabusVersionView.as_view(), name="syllabus_id_version"),
    path("syllabus/version", AllSyllabusVersionsView.as_view(), name="syllabus_version"),
    path(
        "syllabus/<str:syllabus_id>/version/<str:version>.csv",
        SyllabusVersionCSVView.as_view(),
        name="syllabus_id_version_csv",
    ),
    path(
        "syllabus/<str:syllabus_id>/version/<str:version>/preview",
        render_syllabus_preview,
        name="syllabus_id_version_preview",
    ),
    path(
        "syllabus/<str:syllabus_id>/version/<str:version>/fork",
        SyllabusVersionForkView.as_view(),
        name="syllabus_version_fork",
    ),
    path(
        "syllabus/<int:syllabus_id>/version/<int:version>",
        SyllabusVersionView.as_view(),
        name="syllabus_id_version_version",
    ),
    path("syllabus/<str:syllabus_slug>", SyllabusView.as_view(), name="syllabus_slug"),
    path("syllabus/<str:syllabus_slug>/version", SyllabusVersionView.as_view(), name="syllabus_slug_version"),
    path(
        "syllabus/<str:syllabus_slug>/version/<str:version>",
        SyllabusVersionView.as_view(),
        name="syllabus_slug_version_version",
    ),
    path("academy/<int:academy_id>/syllabus", SyllabusView.as_view(), name="academy_id_syllabus"),
    path("academy/<int:academy_id>/syllabus/<int:syllabus_id>", SyllabusView.as_view(), name="academy_id_syllabus_id"),
    path(
        "academy/<int:academy_id>/syllabus/<str:syllabus_slug>", SyllabusView.as_view(), name="academy_id_syllabus_slug"
    ),
    path(
        "academy/<int:academy_id>/syllabus/<int:syllabus_id>/version",
        SyllabusVersionView.as_view(),
        name="academy_id_syllabus_id_version",
    ),
    path(
        "academy/<int:academy_id>/syllabus/<int:syllabus_id>/version/<int:version>",
        SyllabusVersionView.as_view(),
        name="academy_id_syllabus_id_version_version",
    ),
    path(
        "academy/<int:academy_id>/syllabus/<str:syllabus_slug>/version",
        SyllabusVersionView.as_view(),
        name="academy_id_syllabus_slug_version",
    ),
    path(
        "academy/<int:academy_id>/syllabus/<str:syllabus_slug>/version/<str:version>",
        SyllabusVersionView.as_view(),
        name="academy_id_syllabus_slug_version_version",
    ),
    path("catalog/timezones", get_timezones, name="timezones_all"),
    path("catalog/countries", get_countries, name="countries_all"),
    path("catalog/cities", get_cities, name="cities_all"),
    path("report", AcademyReportView.as_view(), name="report_admissions"),
    # replaces an asset slug in all syllabus versions
    path("admin/syllabus/asset/<str:asset_slug>", SyllabusAssetView.as_view(), name="syllabus_asset"),
    # Public Endpoints anyone can call
    path("public/cohort/user", PublicCohortUserView.as_view(), name="public_cohort_user"),
    # Admin Endpoints - Superuser only
    path("admin/cohort", AdminCohortView.as_view(), name="admin_cohort"),
    path("admin/student", AdminStudentView.as_view(), name="admin_student"),
]
