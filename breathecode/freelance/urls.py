from django.contrib import admin
from django.urls import path, include
from .views import (BillView, sync_user_issues, SingleBillView, get_latest_bill, get_issues, render_html_bill,
                    render_html_all_bills, issue_webhook, AcademyProjectView, AcademyProjectMemberView,
                    AcademyProjectInvoiceView)
from rest_framework.authtoken import views

app_name = 'freelance'
urlpatterns = [
    path('bills', BillView.as_view()),
    path('bills/html', render_html_all_bills),
    path('bills/<int:id>/html', render_html_bill),
    path('bills/<int:id>', SingleBillView.as_view()),
    path('issues', get_issues),
    path('sync/user', sync_user_issues),
    path('sync/user/<int:user_id>/bill', get_latest_bill),
    path('academy/project', AcademyProjectView.as_view()),
    path('academy/project/member', AcademyProjectMemberView.as_view()),
    path('academy/project/invoice', AcademyProjectInvoiceView.as_view()),
    path('academy/project/invoice/<int:invoice_id>', AcademyProjectInvoiceView.as_view()),
    path('github/issue_webhook/academy/<slug:academy_slug>', issue_webhook),
]
