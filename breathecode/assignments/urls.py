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
    path("academy/user/<int:user_id>/task", TaskMeView.as_view(), name="academy_user_id_task"),
    path("task/<int:task_id>/deliver/<str:token>", deliver_assignment_view, name="task_id_deliver_token"),
    path("task/<int:task_id>/deliver", TaskMeDeliverView.as_view(), name="task_id_deliver"),
    path("task/<int:task_id>/attachment", TaskMeAttachmentView.as_view(), name="task_id_attachment"),
    path("task/<int:task_id>", TaskMeView.as_view(), name="task_id"),
    path("sync/cohort/<int:cohort_id>/task", sync_cohort_tasks_view, name="sync_cohort_id_task"),
]
