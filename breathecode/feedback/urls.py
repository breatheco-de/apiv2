"""
URL Configuration for Feedback App

This module defines URL patterns following REST conventions with some specific exceptions
for the BreatheCode API v2.

REST Naming Conventions:
========================

1. Resource-based URLs:
   - Use plural nouns for collections: /academy/surveys, /academy/reviews
   - Use singular nouns for individual resources: /survey/<id>

2. HTTP Methods:
   - GET /academy/survey - List all academy surveys
   - POST /academy/survey - Create new survey
   - GET /academy/survey/<id> - Get specific survey
   - PUT/PATCH /academy/survey/<id> - Update specific survey
   - DELETE /academy/survey/<id> - Delete specific survey

3. Nested Resources:
   - /user/me/survey/<id>/questions - Questions for a specific survey
   - /academy/answer/<id> - Answers for academy surveys
   - /academy/survey/template - Survey templates

4. Actions (Non-REST exceptions):
   - /answer/<id>/tracker.png - Track survey opens (GET)
   - /user/me/survey/<id>/questions - Get survey questions (GET)

5. Special Endpoints:
   - /user/me/* - Current user's surveys and answers
   - /academy/* - Academy-specific resources
   - /review* - Review-related endpoints
   - /review_platform* - Review platform endpoints

6. URL Naming:
   - Use snake_case for URL names: academy_survey_id
   - Include resource type and ID when applicable
   - Be descriptive but concise

Examples:
- academy_survey_id - Get/update specific academy survey
- user_me_answer_id - Get/update current user's specific answer
- academy_feedback_settings - Get/update academy feedback settings
- review_platform - Get review platform information
"""

from django.urls import path

from .views import (
    AcademyAnswerView,
    AcademyFeedbackSettingsView,
    AcademyFeedbackTagView,
    AcademySurveyTemplateView,
    AcademySurveyView,
    AnswerMeView,
    GetAnswerView,
    ReviewView,
    get_review_platform,
    get_reviews,
    get_survey,
    get_survey_questions,
    track_survey_open,
)

app_name = "feedback"
urlpatterns = [
    path("academy/answer", GetAnswerView.as_view(), name="answer"),
    path("answer/<int:answer_id>/tracker.png", track_survey_open, name="answer_id_tracker"),
    path("user/me/answer/<int:answer_id>", AnswerMeView.as_view(), name="user_me_answer_id"),
    path("academy/survey", AcademySurveyView.as_view(), name="academy_survey"),
    path("academy/survey/template", AcademySurveyTemplateView.as_view(), name="academy_survey_template"),
    path("academy/survey/<int:survey_id>", AcademySurveyView.as_view(), name="academy_survey_id"),
    path("user/me/survey/<int:survey_id>/questions", get_survey_questions),
    path("user/me/survey/<int:survey_id>", get_survey),
    path("review", get_reviews, name="review"),
    path("academy/review", ReviewView.as_view(), name="review"),
    path("academy/review/<int:review_id>", ReviewView.as_view(), name="review_id"),
    path("review_platform", get_review_platform, name="review_platform"),
    path("review_platform/<str:platform_slug>", get_review_platform, name="review_platform"),
    # TODO: missing tests
    path("academy/answer/<int:answer_id>", AcademyAnswerView.as_view(), name="academy_answer_id"),
    path("academy/feedbacksettings", AcademyFeedbackSettingsView.as_view(), name="academy_feedback_settings"),
    # FeedbackTag endpoints
    path("academy/tag", AcademyFeedbackTagView.as_view(), name="academy_feedback_tag"),
    path("academy/tag/<int:tag_id>", AcademyFeedbackTagView.as_view(), name="academy_feedback_tag_id"),
]
