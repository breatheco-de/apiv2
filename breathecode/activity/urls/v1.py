from django.urls import path

from ..views import ActivityCohortView, ActivityTypeView, ActivityMeView, ActivityClassroomView, StudentActivityView

app_name = "activity"

urlpatterns = [
    path("me", ActivityMeView.as_view(), name="root"),
    path("type/", ActivityTypeView.as_view(), name="type"),
    path("type/<str:activity_slug>", ActivityTypeView.as_view(), name="type_slug"),
    path("academy/cohort/<str:cohort_id>", ActivityClassroomView.as_view(), name="academy_cohort_id"),
    path("academy/student/<str:student_id>", StudentActivityView.as_view(), name="academy_student_id"),
    path("cohort/<str:cohort_id>", ActivityCohortView.as_view(), name="cohort_id"),
]
