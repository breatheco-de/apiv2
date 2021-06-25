from django.contrib import admin
from django.urls import path, include
from .views import (AnswerMeView, GetAnswerView, track_survey_open,
                    get_survey_questions, SurveyView, AcademyAnswerView)

app_name = 'feedback'
urlpatterns = [
    path('academy/answer', GetAnswerView.as_view(), name='answer'),
    path('answer/<int:answer_id>/tracker.png',
         track_survey_open,
         name='answer_id_tracker'),
    path('user/me/answer/<int:answer_id>',
         AnswerMeView.as_view(),
         name='answer_id'),
    path('academy/survey', SurveyView.as_view(), name='academy_survey'),
    path('academy/survey/<int:survey_id>',
         SurveyView.as_view(),
         name='academy_survey_id'),
    path('user/me/survey/<int:survey_id>/questions', get_survey_questions),

    # TODO: missing tests
    path('academy/answer/<int:answer_id>',
         AcademyAnswerView.as_view(),
         name='academy_answer_id'),
]
