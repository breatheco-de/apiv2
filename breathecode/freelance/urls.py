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
