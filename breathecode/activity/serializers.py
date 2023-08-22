import serpy


class ActivitySerializer(serpy.Serializer):
    id = serpy.Field()
    user_id = serpy.Field()
    kind = serpy.Field()
    resource = serpy.Field()
    resource_id = serpy.Field()
    meta = serpy.Field()
    timestamp = serpy.Field()
    duration = serpy.Field()
