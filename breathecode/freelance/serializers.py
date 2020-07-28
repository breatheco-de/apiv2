from .models import Bill
from rest_framework import serializers
import serpy

class BillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bill
        exclude = ()

class SmallUserSerializer(serpy.Serializer):
    id = serpy.Field()

class SmallFreelancerSerializer(serpy.Serializer):
    id = serpy.Field()
    user = SmallUserSerializer()
    
class SmallIssueSerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    title = serpy.Field()
    status = serpy.Field()
    duration_in_minutes = serpy.Field()
    duration_in_hours = serpy.Field()
    url = serpy.Field()
    github_number = serpy.Field()
    freelancer = SmallFreelancerSerializer()
    author = serpy.Field()