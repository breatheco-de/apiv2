from django.contrib import admin
from django.urls import path, include
from .views import (BillView, sync_user_issues, SingleBillView,
                    get_latest_bill, get_issues, render_html_bill)
from rest_framework.authtoken import views

app_name = 'freelance'
urlpatterns = [
    path('bills', BillView.as_view()),
    path('bills/<int:id>/html', render_html_bill),
    path('bills/<int:id>', SingleBillView.as_view()),
    path('issues', get_issues),
    path('sync/user', sync_user_issues),
    path('sync/user/<int:user_id>/bill', get_latest_bill),
]
