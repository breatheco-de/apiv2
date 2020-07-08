from .models import Course
from rest_framework import serializers

class GetCourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        exclude = ()