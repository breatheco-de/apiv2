from django.urls import path
from .views import (
    AcademyProvisioningUserConsumptionView,
    AcademyBillView,
    UploadView,
    redirect_new_container,
    redirect_new_container_public,
    redirect_workspaces,
    render_html_all_bills,
    render_html_bill,
)

app_name = "provisioning"
urlpatterns = [
    path("me/container/new", redirect_new_container),
    path("public/container/new", redirect_new_container_public),
    path("me/workspaces", redirect_workspaces),
    path("admin/upload", UploadView.as_view(), name="admin_upload"),
    path("academy/userconsumption", AcademyProvisioningUserConsumptionView.as_view(), name="academy_userconsumption"),
    path("academy/bill", AcademyBillView.as_view(), name="academy_bill_id"),
    path("academy/bill/<int:bill_id>", AcademyBillView.as_view(), name="academy_bill_id"),
    path("bill/html", render_html_all_bills, name="bill_html"),
    path("bill/<int:id>/html", render_html_bill, name="bill_id_html"),
    # path('academy/me/container', ContainerMeView.as_view()),
    # path('me/container', ContainerMeView.as_view()),
    # path('me/container/<int:container_id>', ContainerMeView.as_view()),
]
