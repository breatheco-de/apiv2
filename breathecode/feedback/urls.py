from django.contrib import admin
from django.urls import path, include
from .views import AnswerView, GetAnswerView, track_survey_open

app_name='feedback'
urlpatterns = [
    path('answer', GetAnswerView.as_view(), name='answer'),
    path('answer/<int:answer_id>/tracker.png', track_survey_open, name='answer_id_tracker'),
    path('answer/<int:answer_id>', AnswerView.as_view(), name='answer_id'),
]
