import serpy


class ActivitySerializer(serpy.Serializer):
    id = serpy.Field()
    user_id = serpy.Field()
    kind = serpy.Field()
    related = serpy.Field()
    meta = serpy.MethodField()
    timestamp = serpy.Field()

    def get_meta(self, obj):
        res = {}

        for key in obj.meta:
            if obj.meta[key] is not None:
                res[key] = obj.meta[key]

        return res
