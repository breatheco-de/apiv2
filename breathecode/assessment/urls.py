from django.urls import path
from .views import (track_assesment_open, GetAssessmentView, GetThresholdView, AssessmentQuestionView,
                    AssessmentOptionView)

app_name = 'assessment'
urlpatterns = [
    # user assessments
    path('user/assesment/<int:user_assessment_id>/tracker.png', track_assesment_open),
    path('', GetAssessmentView.as_view()),
    path('<str:assessment_slug>/threshold', GetThresholdView.as_view()),
    path('<str:assessment_slug>', GetAssessmentView.as_view()),
    path('<str:assessment_slug>/question/<int:question_id>', AssessmentQuestionView.as_view()),
    path('<str:assessment_slug>/option/<int:option_id>', AssessmentOptionView.as_view()),
]
