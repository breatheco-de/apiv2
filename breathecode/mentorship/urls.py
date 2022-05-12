from django.contrib import admin
from django.urls import path, include
from .views import (ServiceView, MentorView, SessionView, render_html_bill, BillView, ServiceSessionView,
                    MentorSessionView)

app_name = 'mentorship'
urlpatterns = [
    path('academy/service', ServiceView.as_view(), name='academy_service'),
    path('academy/mentor', MentorView.as_view(), name='academy_mentor'),
    path('academy/session', SessionView.as_view(), name='academy_session'),
    path('academy/mentor/<int:mentor_id>/session', MentorSessionView.as_view(),
         name='academy_mentor_session'),
    path('academy/service/<int:service_id>/session',
         ServiceSessionView.as_view(),
         name='academy_service_session'),
    path('academy/bill/<int:id>/html', render_html_bill),
    path('academy/service/<int:service_id>', ServiceView.as_view(), name='academy_service_id'),
    path('academy/mentor/<int:mentor_id>/bill', BillView.as_view(), name='generate_mentor_bill'),
    path('academy/mentor/<int:mentor_id>', MentorView.as_view(), name='academy_mentor_id'),
    path('academy/bill', BillView.as_view(), name='academy_bill'),
    path('academy/bill/<int:bill_id>', BillView.as_view(), name='academy_bill_id'),
    path('academy/session/<int:session_id>', SessionView.as_view(), name='academy_session_id'),
]
