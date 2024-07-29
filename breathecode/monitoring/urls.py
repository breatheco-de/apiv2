from django.urls import path
from .views import (
    get_apps,
    get_endpoints,
    get_download,
    get_upload,
    process_github_webhook,
    process_stripe_webhook,
    RepositorySubscriptionView,
)

app_name = "monitoring"
urlpatterns = [
    path("application", get_apps),
    path("endpoint", get_endpoints),
    path("download", get_download),
    path("download/<int:download_id>", get_download),
    path("upload", get_upload),
    path("upload/<int:upload_id>", get_upload),
    path("reposubscription", RepositorySubscriptionView.as_view()),
    path("reposubscription/<int:subscription_id>", RepositorySubscriptionView.as_view()),
    path("github/webhook/<str:subscription_token>", process_github_webhook),
    path("stripe/webhook", process_stripe_webhook, name="stripe_webhook"),
]
