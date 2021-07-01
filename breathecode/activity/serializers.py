from rest_framework import serializers
import serpy


class ActivitySerializer(serpy.Serializer):
    id = serpy.Field()
    # comment = serpy.Field()
    # score = serpy.Field()
    # user_id = serpy.Field()

    # certificate_slug = serpy.Field(required=False)
    # academy_slug = serpy.Field(required=False)
    # cohort_slug = serpy.Field(required=False)
    # mentor_id = serpy.Field(required=False)
