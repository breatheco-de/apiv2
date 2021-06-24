from django.contrib import admin
from django.urls import path, include
from .views import track_assesment_open, GetAssessmentView

app_name = 'assessment'
urlpatterns = [
    # user assessments
    path('user/assesment/<int:user_assessment_id>/tracker.png',
         track_assesment_open),
    path('', GetAssessmentView.as_view()),
    path('<str:assessment_slug>', GetAssessmentView.as_view()),
]
