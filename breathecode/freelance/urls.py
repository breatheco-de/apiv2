"""
URL Configuration for Freelance App

This module defines URL patterns following REST conventions with some specific exceptions
for the BreatheCode API v2.

REST Naming Conventions:
========================

1. Resource-based URLs:
   - Use plural nouns for collections: /bills, /academy/projects
   - Use singular nouns for individual resources: /bill/<id>

2. HTTP Methods:
   - GET /bills - List all bills
   - POST /bills - Create new bill
   - GET /bills/<id> - Get specific bill
   - PUT/PATCH /bills/<id> - Update specific bill
   - DELETE /bills/<id> - Delete specific bill

3. Nested Resources:
   - /academy/project/<id>/invoice - Invoices for specific project
   - /academy/project/invoice/<id>/member - Members for specific invoice
   - /academy/project/member - Project members management

4. Actions (Non-REST exceptions):
   - /bills/html - Render all bills as HTML (GET)
   - /bills/<id>/html - Render specific bill as HTML (GET)
   - /sync/user - Sync user issues (POST)
   - /sync/user/<id>/bill - Get latest bill for user (GET)

5. Special Endpoints:
   - /academy/* - Academy-specific resources
   - /bills/* - Bill management and rendering
   - /invoice/* - Invoice management
   - /issues - Issue tracking
   - /sync/* - Synchronization endpoints

6. URL Naming:
   - Use snake_case for URL names: academy_project_id
   - Include resource type and ID when applicable
   - Be descriptive but concise

Examples:
- academy_project_id - Get/update specific academy project
- academy_project_invoice_id - Get/update specific project invoice
- academy_project_invoice_id_member - Get/update invoice members
- bills_html - Render all bills as HTML
"""

from django.urls import path

from .views import (
    AcademyBillView,
    AcademyInvoiceMemberView,
    AcademyProjectInvoiceView,
    AcademyProjectMemberView,
    AcademyProjectView,
    BillView,
    SingleBillView,
    SingleInvoiceView,
    get_issues,
    get_latest_bill,
    render_html_all_bills,
    render_html_bill,
    sync_user_issues,
)

app_name = "freelance"
urlpatterns = [
    path("bills", BillView.as_view()),
    path("bills/html", render_html_all_bills),
    path("bills/<int:id>/html", render_html_bill),
    path("bills/<int:id>", SingleBillView.as_view()),
    path("invoice/<int:id>", SingleInvoiceView.as_view()),
    path("issues", get_issues),
    path("sync/user", sync_user_issues),
    path("sync/user/<int:user_id>/bill", get_latest_bill),
    path("academy/bill", AcademyBillView.as_view()),
    path("academy/bill/<int:bill_id>", AcademyBillView.as_view()),
    path("academy/project", AcademyProjectView.as_view()),
    path("academy/project/<int:project_id>", AcademyProjectView.as_view()),
    path("academy/project/member", AcademyProjectMemberView.as_view()),
    path("academy/project/invoice", AcademyProjectInvoiceView.as_view()),
    path("academy/project/<int:project_id>/invoice", AcademyProjectInvoiceView.as_view()),
    path("academy/project/invoice/<int:invoice_id>", AcademyProjectInvoiceView.as_view()),
    path("academy/project/invoice/<int:invoice_id>/member", AcademyInvoiceMemberView.as_view()),
]
