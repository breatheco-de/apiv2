import serpy, logging, hashlib, re
from django.utils import timezone
from .models import CSVDownload
from breathecode.admissions.models import Academy
from rest_framework import serializers
from breathecode.utils.validation_exception import ValidationException

logger = logging.getLogger(__name__)


class CSVDownloadSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    name = serpy.Field()
    url = serpy.Field()
    status = serpy.Field()
    created_at = serpy.Field()
    finished_at = serpy.Field()

class CSVUploadSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    name = serpy.Field()
    url = serpy.Field()
    status = serpy.Field()
    status_message = serpy.Field()
    created_at = serpy.Field()
    finished_at = serpy.Field()
