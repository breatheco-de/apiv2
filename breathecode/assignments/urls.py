"""
URL Configuration for Assignments App

This module defines URL patterns following REST conventions with some specific exceptions
for the BreatheCode API v2.

REST Naming Conventions:
========================

1. Resource-based URLs:
   - Use plural nouns for collections: /academy/tasks, /academy/coderevisions
   - Use singular nouns for individual resources: /task/<id>

2. HTTP Methods:
   - GET /academy/task - List all academy tasks
   - POST /academy/task - Create new task
   - GET /academy/task/<id> - Get specific task
   - PUT/PATCH /academy/task/<id> - Update specific task
   - DELETE /academy/task/<id> - Delete specific task

3. Nested Resources:
   - /user/me/task/<id> - Current user's specific task
   - /academy/task/<id>/commitfile - Files for a specific task
   - /academy/cohort/<id>/task - Tasks for a specific cohort

4. Actions (Non-REST exceptions):
   - /task/<id>/deliver - Deliver task assignment (POST)
   - /task/<id>/deliver/<token> - Deliver with token (POST)
   - /sync/cohort/<id>/task - Sync cohort tasks (POST)

5. Special Endpoints:
   - /user/me/* - Current user's assignments and tasks
   - /academy/* - Academy-specific resources
   - /me/* - Current user's resources (shorter prefix)
   - /sync/* - Synchronization endpoints

6. URL Naming:
   - Use snake_case for URL names: academy_task_id_commitfile
   - Include resource type and ID when applicable
   - Be descriptive but concise

Examples:
- academy_task_id_commitfile - Get/update commit files for specific task
- user_me_task_id - Get/update current user's specific task
- academy_coderevision_id - Get/update specific code revision
- sync_cohort_id_task - Sync tasks for specific cohort
"""

from django.urls import path

from .views import (
    AcademyCodeRevisionView,
    AcademyCommitFileView,
    CohortTaskView,
    FinalProjectMeView,
    FinalProjectScreenshotView,
    MeCodeRevisionRateView,
    MeCodeRevisionView,
    MeCommitFileView,
    SubtaskMeView,
    TaskMeAttachmentView,
    TaskMeDeliverView,
    TaskMeView,
    TaskTeacherView,
    deliver_assignment_view,
    sync_cohort_tasks_view,
    AssignmentTelemetryView,
    FinalProjectCohortView,
    CompletionJobView,
    SyncTasksView,
    RepositoryDeletionsMeView,
    FlagView,
    AssetFlagView,
    LegacyFlagAssetView,
)

app_name = "assignments"
urlpatterns = [
    path("task/", TaskTeacherView.as_view(), name="task"),
    path("user/me/task", TaskMeView.as_view(), name="user_me_task"),
    path("user/me/final_project", FinalProjectMeView.as_view(), name="user_me_final_project"),
    path(
        "user/me/final_project/screenshot",
        FinalProjectScreenshotView.as_view(),
        name="user_me_final_project_screenshot",
    ),
    path("user/me/final_project/<int:project_id>", FinalProjectMeView.as_view(), name="user_me_project"),
    path("user/me/task/<int:task_id>", TaskMeView.as_view(), name="user_me_task_id"),
    path("user/me/task/<int:task_id>/subtasks", SubtaskMeView.as_view(), name="user_me_task_id"),
    path("me/telemetry", AssignmentTelemetryView.as_view(), name="me_telemetry"),
    path("me/task/<int:task_id>/commitfile", MeCommitFileView.as_view(), name="me_task_id_commitfile"),
    path("me/commitfile/<int:commitfile_id>", MeCommitFileView.as_view(), name="me_commitfile_id"),
    path("academy/task/<int:task_id>/commitfile", AcademyCommitFileView.as_view(), name="academy_task_id_commitfile"),
    path(
        "academy/task/<int:task_id>/commitfile/<int:commitfile_id>",
        AcademyCommitFileView.as_view(),
        name="academy_commitfile_id",
    ),
    path("me/coderevision", MeCodeRevisionView.as_view(), name="me_coderevision"),
    path("me/task/<int:task_id>/coderevision", MeCodeRevisionView.as_view(), name="me_task_id_coderevision"),
    path(
        "me/coderevision/<int:coderevision_id>/rate", MeCodeRevisionRateView.as_view(), name="me_coderevision_id_rate"
    ),
    path("academy/coderevision", AcademyCodeRevisionView.as_view(), name="academy_coderevision"),
    path(
        "academy/task/<int:task_id>/coderevision",
        AcademyCodeRevisionView.as_view(),
        name="academy_task_id_coderevision",
    ),
    path(
        "academy/coderevision/<int:coderevision_id>", AcademyCodeRevisionView.as_view(), name="academy_coderevision_id"
    ),
    path("user/<int:user_id>/task", TaskMeView.as_view(), name="user_id_task"),
    path("user/<int:user_id>/task/<int:task_id>", TaskMeView.as_view(), name="user_id_task_id"),
    path("academy/cohort/<int:cohort_id>/task", CohortTaskView.as_view()),
    path("academy/cohort/<int:cohort_id>/final_project", FinalProjectCohortView.as_view(), name="final_project_cohort"),
    path(
        "academy/cohort/<int:cohort_id>/final_project/<int:final_project_id>",
        FinalProjectCohortView.as_view(),
        name="final_project_cohort_update",
    ),
    path("academy/cohort/<int:cohort_id>/synctasks", SyncTasksView.as_view(), name="sync_cohort_tasks"),
    path("academy/user/<int:user_id>/task", TaskMeView.as_view(), name="academy_user_id_task"),
    path("task/<int:task_id>/deliver/<str:token>", deliver_assignment_view, name="task_id_deliver_token"),
    path("task/<int:task_id>/deliver", TaskMeDeliverView.as_view(), name="task_id_deliver"),
    path("task/<int:task_id>/attachment", TaskMeAttachmentView.as_view(), name="task_id_attachment"),
    path("task/<int:task_id>", TaskMeView.as_view(), name="task_id"),
    path("sync/cohort/<int:cohort_id>/task", sync_cohort_tasks_view, name="sync_cohort_id_task"),
    path("completion_job/<int:task_id>", CompletionJobView.as_view(), name="completion_job"),
    path("me/deletion_order", RepositoryDeletionsMeView.as_view(), name="me_deletion_order"),
    path("academy/flag", FlagView.as_view(), name="flag"),
    path("academy/asset/flag", AssetFlagView.as_view(), name="flag_asset"),
    path("academy/asset/<str:asset_id>/flag/legacy", LegacyFlagAssetView.as_view(), name="flag_asset_legacy"),
]
