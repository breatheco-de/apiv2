from django.urls import path
from .views import AnswerDetailView, AnswerListView, track_survey_open

app_name='feedback'
urlpatterns = [
    path('answer', AnswerListView.as_view(), name='answer'),
    path('answer/<int:answer_id>/tracker.png', track_survey_open, name='answer_id_tracker'),
    path('answer/<int:answer_id>', AnswerDetailView.as_view(), name='answer_id'),
]
