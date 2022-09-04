from django.urls import path
from .views import (ServiceView, MentorView, SessionView, render_html_bill, BillView, ServiceSessionView,
                    MentorSessionView, UserMeSessionView, UserMeBillView, PublicMentorView)

app_name = 'mentorship'
urlpatterns = [
    path('academy/service', ServiceView.as_view(), name='academy_service'),
    path('academy/service/<int:service_id>', ServiceView.as_view(), name='academy_service_id'),
    path('academy/mentor', MentorView.as_view(), name='academy_mentor'),
    path('academy/mentor/<int:mentor_id>', MentorView.as_view(), name='academy_mentor_id'),
    path('academy/mentor/<int:mentor_id>/session',
         MentorSessionView.as_view(),
         name='academy_mentor_id_session'),
    path('academy/session', SessionView.as_view(), name='academy_session'),
    path('academy/session/<int:session_id>', SessionView.as_view(), name='academy_session_id'),
    path('academy/service/<int:service_id>/session',
         ServiceSessionView.as_view(),
         name='academy_service_id_session'),
    path('academy/bill', BillView.as_view(), name='academy_bill'),
    path('academy/bill/<int:bill_id>', BillView.as_view(), name='academy_bill_id'),
    path('academy/bill/<int:id>/html', render_html_bill, name='academy_bill_id_html'),
    path('academy/mentor/<int:mentor_id>/bill', BillView.as_view(), name='academy_mentor_id_bill'),
    path('user/me/session', UserMeSessionView.as_view(), name='user_session'),
    path('user/me/bill', UserMeBillView.as_view(), name='user_bill'),

    # Public Endpoints for marketing purposes
    path('public/mentor', PublicMentorView.as_view(), name='public_mentor'),
]
