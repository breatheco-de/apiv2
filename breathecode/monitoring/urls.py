from django.urls import path

from .views import (
    AcademyDownloadSignedUrlView,
    AcademyDownloadView,
    DjangoAdminView,
    RepositorySubscriptionView,
    get_apps,
    get_download,
    get_endpoints,
    get_upload,
    process_github_webhook,
    process_stripe_webhook,
)

app_name = "monitoring"
urlpatterns = [
    path("admin/actions", DjangoAdminView.as_view(), name="admin_actions"),
    path("application", get_apps),
    path("endpoint", get_endpoints),
    path("download", get_download),
    path("download/<int:download_id>", get_download),
    path("academy/download", AcademyDownloadView.as_view(), name="academy_download"),
    path("academy/download/<int:download_id>", AcademyDownloadView.as_view(), name="academy_download_id"),
    path("academy/download/<int:download_id>/signed-url", AcademyDownloadSignedUrlView.as_view(), name="academy_download_signed_url"),
    path("upload", get_upload),
    path("upload/<int:upload_id>", get_upload),
    path("reposubscription", RepositorySubscriptionView.as_view()),
    path("reposubscription/<int:subscription_id>", RepositorySubscriptionView.as_view()),
    path("github/webhook/<str:subscription_token>", process_github_webhook),
    path("stripe/webhook", process_stripe_webhook, name="stripe_webhook"),
]
