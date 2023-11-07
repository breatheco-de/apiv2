import serpy, logging

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
