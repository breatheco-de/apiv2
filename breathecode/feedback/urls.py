from django.contrib import admin
from django.urls import path, include
from .views import AnswerView, GetAnswerView, track_survey_open

app_name='feedback'
urlpatterns = [
    path('answer', GetAnswerView.as_view()),
    path('answer/<int:answer_id>/tracker.png', track_survey_open),
    path('answer/<int:answer_id>', AnswerView.as_view()),
]

