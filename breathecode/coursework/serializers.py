from .models import Course, Syllabus
from rest_framework import serializers
import serpy

class GetCourseSerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()
    logo = serpy.Field()
    duration_in_hours = serpy.Field()
    duration_in_days = serpy.Field()
    week_hours = serpy.Field()
    updated_at = serpy.Field()
    created_at = serpy.Field()

class SyllabusGetSerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    version = serpy.Field()
    course = serpy.MethodField()
    updated_at = serpy.Field()
    json = serpy.Field()

    def get_course(self, obj):
        return obj.course.slug

class SyllabusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Syllabus
        exclude = ()
        extra_kwargs = {
            'course': {'read_only': True},
        }

    def create(self, validated_data):
        return super(SyllabusSerializer, self).create({ **validated_data, "course": self.context['course'] })

class SyllabusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Syllabus
        exclude = ()
        extra_kwargs = {
            'course': {'read_only': True},
            'version': {'read_only': True},
        }

class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        exclude = ()
