import serpy


class MySerializer(serpy.Serializer):
    id = serpy.IntField()
    name = serpy.StrField()
    value = serpy.IntField()
