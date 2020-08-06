from django.contrib import admin
from django.urls import path, include
from .views import AnswerView

app_name='feedback'
urlpatterns = [
    path('answer/', AnswerView.as_view()),
]

