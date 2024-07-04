from django.contrib.staticfiles.storage import ManifestFilesMixin
from storages.backends.gcloud import GoogleCloudStorage

__all__ = ["GCSManifestStaticFilesStorage"]


class GCSManifestStaticFilesStorage(ManifestFilesMixin, GoogleCloudStorage):
    pass
