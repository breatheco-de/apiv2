from django.contrib import admin
from django.urls import path, include
from .views import track_assesment_open, GetAssessmentView

app_name='assessment'
urlpatterns = [
    path('assesment', GetAssessmentView.as_view()),
    path('/assesment/<int:assessment_id>', GetAssessmentView.as_view()),

    # user assessments
    path('/user/assesment/<int:user_assessment_id>/tracker.png', track_assesment_open),
]

