from django.shortcuts import render
from .models import Course
from rest_framework.decorators import api_view

@api_view(['GET'])
def get_courses(request):
    courses = Course.objects.all()
    serializer = GetCourseSerializer(courses, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)