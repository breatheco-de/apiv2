from django.shortcuts import render
from .models import Course, Syllabus
from .serializers import SyllabusSerializer, GetCourseSerializer, SyllabusGetSerializer, SyllabusSmallSerializer
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status, serializers
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from breathecode.utils import capable_of, ValidationException
from breathecode.admissions.models import Academy

@api_view(['GET'])
def get_courses(request):
    courses = Course.objects.all()
    serializer = GetCourseSerializer(courses, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
def get_single_course(request, course_slug):
    course = Course.objects.filter(slug=course_slug).first()
    if course is None:
        raise serializers.ValidationError("Course slug not found", code=404)
    serializer = GetCourseSerializer(course, many=False)
    return Response(serializer.data, status=status.HTTP_200_OK)

class SyllabusView(APIView):
    """
    List all snippets, or create a new snippet.
    """

    # TODO: uncomment decorator when finally all students have a ProfileAcademy object.
    # @capable_of('crud_syllabus')
    def get(self, request, course_slug=None, version=None, academy_id=None):
        if academy_id is None:
            raise ValidationException("Missing academy id")
        
        course = Course.objects.filter(slug=course_slug).first()
        if course is None:
            raise serializers.ValidationError("Course slug not found", code=404)

        syl = None
        if version is None:
            syl = course.syllabus_set.filter(academy_owner__id=academy_id)
            serializer = SyllabusSmallSerializer(syl, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            syl = course.syllabus_set.filter(version=version, academy_owner__id=academy_id).first()
        
        if syl is None:
            raise serializers.ValidationError("Syllabus not found", code=404)

        # TODO: if a syllabus is private, no other academy should be able to see it

        serializer = SyllabusGetSerializer(syl, many=False)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @capable_of('crud_syllabus')
    def post(self, request, course_slug=None, academy_id=None):
        version = 1
        course = Course.objects.filter(slug=course_slug).first()
        if course is None:
            raise serializers.ValidationError(f"Invalid course slug {course__slug}", code=404)

        item = Syllabus.objects.filter(course__slug=course_slug, academy_owner__id=academy_id).order_by('version').first()
        if item is not None:
            version = item.version + 1

        academy = Academy.objects.filter(id=academy_id).first()
        if academy is None:
            raise ValidationException(f"Invalid academy {str(academy_id)}")

        serializer = SyllabusSerializer(data=request.data, context={"course": course, "academy": academy })
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of('crud_syllabus')
    def put(self, request, course_slug=None, version=None, academy_id=None):
        if version is None:
            raise serializers.ValidationError("Missing syllabus version", code=400)
        
        item = Syllabus.objects.filter(course__slug=course_slug, version=version, academy_owner__id=academy_id).first()
        if item is None:
            raise serializers.ValidationError("Syllabus version not found for this academy", code=404)
        
        serializer = SyllabusSerializer(item, data=request.data, many=False)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
