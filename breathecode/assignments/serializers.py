import serpy
from rest_framework import serializers
from .models import Task

class SmallTaskSerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    title = serpy.Field()
    task_status = serpy.Field()
    associated_slug = serpy.Field()
    revision_status = serpy.Field()
    task_type = serpy.Field()

class PostTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ['id', 'title', 'task_status', 'associated_slug']