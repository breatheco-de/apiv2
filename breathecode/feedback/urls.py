from django.urls import path
from .views import (
    AnswerMeView,
    GetAnswerView,
    track_survey_open,
    get_survey_questions,
    SurveyView,
    AcademyAnswerView,
    get_reviews,
    ReviewView,
    get_review_platform,
)

app_name = "feedback"
urlpatterns = [
    path("academy/answer", GetAnswerView.as_view(), name="answer"),
    path("answer/<int:answer_id>/tracker.png", track_survey_open, name="answer_id_tracker"),
    path("user/me/answer/<int:answer_id>", AnswerMeView.as_view(), name="user_me_answer_id"),
    path("academy/survey", SurveyView.as_view(), name="academy_survey"),
    path("academy/survey/<int:survey_id>", SurveyView.as_view(), name="academy_survey_id"),
    path("user/me/survey/<int:survey_id>/questions", get_survey_questions),
    path("review", get_reviews, name="review"),
    path("academy/review", ReviewView.as_view(), name="review"),
    path("academy/review/<int:review_id>", ReviewView.as_view(), name="review_id"),
    path("review_platform", get_review_platform, name="review_platform"),
    path("review_platform/<str:platform_slug>", get_review_platform, name="review_platform"),
    # TODO: missing tests
    path("academy/answer/<int:answer_id>", AcademyAnswerView.as_view(), name="academy_answer_id"),
]
