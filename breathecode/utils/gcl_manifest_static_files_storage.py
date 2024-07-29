from storages.backends.gcloud import GoogleCloudStorage
from django.contrib.staticfiles.storage import ManifestFilesMixin

__all__ = ["GCSManifestStaticFilesStorage"]


class GCSManifestStaticFilesStorage(ManifestFilesMixin, GoogleCloudStorage):
    pass
