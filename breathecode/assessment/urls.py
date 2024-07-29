from django.urls import path
from .views import (
    TrackAssessmentView,
    GetAssessmentView,
    GetThresholdView,
    AssessmentQuestionView,
    AssessmentOptionView,
    AcademyUserAssessmentView,
    AssessmentLayoutView,
    AcademyAssessmentLayoutView,
    AnswerView,
    AcademyAnswerView,
)

app_name = "assessment"
urlpatterns = [
    # user assessments
    path("user/assessment", TrackAssessmentView.as_view()),
    path("user/assessment/<str:ua_token>", TrackAssessmentView.as_view()),
    path("user/assessment/<str:token>/answer", AnswerView.as_view()),
    path("user/assessment/<str:token>/answer/<int:answer_id>", AnswerView.as_view()),
    path("academy/user/assessment/<int:user_assessment_id>/answer/<int:answer_id>", AcademyAnswerView.as_view()),
    path("academy/user/assessment", AcademyUserAssessmentView.as_view()),
    path("academy/user/assessment/<int:ua_id>", AcademyUserAssessmentView.as_view()),
    path("", GetAssessmentView.as_view()),
    path("layout/<str:layout_slug>", AssessmentLayoutView.as_view()),
    path("academy/layout", AcademyAssessmentLayoutView.as_view()),
    path("academy/layout/<str:layout_slug>", AcademyAssessmentLayoutView.as_view()),
    path("<str:assessment_slug>/threshold", GetThresholdView.as_view()),
    path("<str:assessment_slug>/threshold/<int:threshold_id>", GetThresholdView.as_view()),
    path("<str:assessment_slug>/question/<int:question_id>", AssessmentQuestionView.as_view()),
    path("<str:assessment_slug>/option/<int:option_id>", AssessmentOptionView.as_view()),
    path("<str:assessment_slug>", GetAssessmentView.as_view()),
]
