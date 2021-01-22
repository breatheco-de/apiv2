from .models import Course, Syllabus
from rest_framework import serializers
from breathecode.utils import ValidationException
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

class SyllabusSmallSerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    version = serpy.Field()
    updated_at = serpy.Field()

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
            'version': {'read_only': True},
        }

    def create(self, validated_data):
        previous_syllabus = Syllabus.objects.filter(course__id=self.context['course'].id, academy_owner=self.context['academy']).order_by('-version').first()
        version = 1
        if previous_syllabus is not None:
            version = previous_syllabus.version + 1
        return super(SyllabusSerializer, self).create({ 
            **validated_data,
            "course": self.context['course'],
            "academy_owner": self.context['academy'],
            "version": version
        })

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
