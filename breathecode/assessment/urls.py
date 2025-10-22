"""
URL Configuration for Assessment App

This module defines URL patterns following REST conventions with some specific exceptions
for the BreatheCode API v2.

REST Naming Conventions:
========================

1. Resource-based URLs:
   - Use plural nouns for collections: /academy/layouts, /academy/assessments
   - Use singular nouns for individual resources: /assessment/<slug>

2. HTTP Methods:
   - GET /academy/layout - List all academy assessment layouts
   - POST /academy/layout - Create new layout
   - GET /academy/layout/<slug> - Get specific layout
   - PUT/PATCH /academy/layout/<slug> - Update specific layout
   - DELETE /academy/layout/<slug> - Delete specific layout

3. Nested Resources:
   - /user/assessment/<token>/answer - Answers for specific assessment
   - /academy/user/assessment/<id>/answer/<id> - Academy answer management
   - /<slug>/question/<id> - Questions for specific assessment
   - /<slug>/threshold/<id> - Thresholds for specific assessment

4. Actions (Non-REST exceptions):
   - /user/assessment - Track user assessment (POST)
   - /user/assessment/<token> - Track specific assessment (POST)
   - /<slug>/threshold - Get assessment thresholds (GET)

5. Special Endpoints:
   - /user/* - User-specific assessments
   - /academy/* - Academy-specific resources
   - /layout/* - Assessment layout endpoints
   - Root endpoint - Public assessment access

6. URL Naming:
   - Use snake_case for URL names: academy_layout_slug
   - Include resource type and ID when applicable
   - Be descriptive but concise

Examples:
- academy_layout_slug - Get/update specific assessment layout
- academy_user_assessment_id - Get/update specific user assessment
- assessment_slug_question_id - Get/update specific assessment question
"""

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
