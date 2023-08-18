from django.urls import path

from breathecode.utils.router.router import Router
from .views import (ActivityCohortView, ActivityTypeView, ActivityMeView, ActivityClassroomView,
                    StudentActivityView, V2ActivityView)

app_name = 'activity'
router = Router('activity') \
    .set_version(1) \
    .release([
        path('me', ActivityMeView.as_view(), name='root'),
        path('type/', ActivityTypeView.as_view(), name='type'),
        path('type/<str:activity_slug>', ActivityTypeView.as_view(), name='type_slug'),
        path('academy/cohort/<str:cohort_id>', ActivityClassroomView.as_view(), name='academy_cohort_id'),
        path('academy/student/<str:student_id>', StudentActivityView.as_view(), name='academy_student_id'),
        path('cohort/<str:cohort_id>', ActivityCohortView.as_view(), name='cohort_id')
    ]) \
    .release([
        path('', V2ActivityView.as_view(), name='root'),
        path('<str:activity_slug>', V2ActivityView.as_view(), name='root'),

    ])
