from django.contrib import admin
from django.urls import path, include
from .views import test_email, preview_template

app_name='notify'
urlpatterns = [
    path('preview/<slug>', preview_template),
    path('test/email/<email>', test_email),
]

