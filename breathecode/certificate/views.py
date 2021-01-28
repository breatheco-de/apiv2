import logging
from django.shortcuts import render
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Specialty, Badge, UserSpecialty
from breathecode.admissions.models import CohortUser
from breathecode.utils import capable_of
from .serializers import SpecialtySerializer, UserSpecialtySerializer, UserSmallSerializer
from rest_framework.exceptions import NotFound
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status, serializers
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from .tasks import take_screenshot
from .actions import generate_certificate

logger = logging.getLogger(__name__)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_specialties(request):
    items = Specialty.objects.all()
    serializer = SpecialtySerializer(items, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_badges(request):
    items = Badge.objects.all()
    serializer = SpecialtySerializer(items, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_certificate(request, token):
    item = UserSpecialty.objects.filter(token=token).first()
    if item is None:
        raise NotFound('Certificate not found')

    serializer = UserSpecialtySerializer(item)
    return Response(serializer.data, status=status.HTTP_200_OK)

@receiver(post_save, sender=UserSpecialty)
def post_save_course_dosomething(sender,instance, **kwargs):
    if instance.preview_url is None or instance.preview_url == "":
        take_screenshot.delay(instance.id)

class CertificateView(APIView):
    """
    List all snippets, or create a new snippet.
    """
    @capable_of('read_certificate')
    def get(self, request, cohort_id, student_id, academy_id=None):

        cert = UserSpecialty.objects.filter(cohort__id=cohort_id, user__id=student_id, cohort__academy__id=academy_id)
        if cert is None:
            raise serializers.ValidationError("Certificate not found", code=404)

        serializer = UserSpecialtySerializer(cert, many=False)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @capable_of('crud_certificate')
    def post(self, request, cohort_id, student_id, academy_id=None):

        cu = CohortUser.objects.filter(cohort__id=cohort_id, user__id=student_id, role="STUDENT", cohort__academy__id=academy_id)
        if cu is None:
            raise serializers.ValidationError(f"Student not found for this cohort", code=404)

        cert = generate_certificate(cu.user, cu.cohort)
        serializer = UserSpecialtySerializer(cert, many=False)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class CertificateCohortView(APIView):
    """
    List all snippets, or create a new snippet.
    """
    @capable_of('read_certificate')
    def get(self, request, cohort_id, academy_id=None):

        cert = UserSpecialty.objects.filter(cohort__id=cohort_id, cohort__academy__id=academy_id)
        serializer = UserSpecialtySerializer(cert, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @capable_of('crud_certificate')
    def post(self, request, cohort_id, academy_id=None):

        cohort_users = CohortUser.objects.filter(cohort__id=cohort_id, role='STUDENT',
            educational_status='GRADUATED', cohort__academy__id=academy_id)
        logger.debug(f"Generating gertificate for {str(cohort_users.count())} students that GRADUATED")
        certificates = {
            "success": [],
            "error": [],
        }
        for cu in cohort_users:
            try:
                cert = generate_certificate(cu.user, cu.cohort)
                serializer = UserSpecialtySerializer(cert, many=False)
                certificates["success"].append(serializer.data)
            except Exception as e:
                err = UserSmallSerializer(cu.user, many=False).data
                certificates["error"].append({ **err, "msg": str(e) })
                logger.exception(f"Error generating certificate for {str(cu.user.id)} cohort {str(cu.cohort.id)}")

        return Response(certificates, status=status.HTTP_201_CREATED)

class CertificateAcademyView(APIView):
    """
    List all snippets, or create a new snippet.
    """
    @capable_of('read_certificate')
    def get(self, request, academy_id=None):
        # print(request.headers['Academy'])
        cert = UserSpecialty.objects.filter(cohort__academy__id=academy_id)
        serializer = UserSpecialtySerializer(cert, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


# class SyllabusView(APIView):
#     """
#     List all snippets, or create a new snippet.
#     """
#     def get(self, request, course_slug=None, version=None):
#         course = Course.objects.filter(slug=course_slug).first()
#         if course is None:
#             raise serializers.ValidationError("Course slug not found", code=404)

#         syl = None
#         if version is None:
#             syl = course.syllabus_set.all()
#             serializer = SyllabusSmallSerializer(syl, many=True)
#             return Response(serializer.data, status=status.HTTP_200_OK)
#         else:
#             syl = course.syllabus_set.filter(version=version).first()
        
#         if syl is None:
#             raise serializers.ValidationError("Syllabus not found", code=404)

#         serializer = SyllabusGetSerializer(syl, many=False)
#         return Response(serializer.data, status=status.HTTP_200_OK)
#     def post(self, request, course_slug=None):
#         version = 1
#         course = Course.objects.filter(slug=course_slug).first()
#         if course is None:
#             raise serializers.ValidationError(f"Invalid course slug {course__slug}", code=404)

#         item = Syllabus.objects.filter(course__slug=course_slug).order_by('version').first()

#         if item is not None:
#             version = item.version + 1

#         serializer = SyllabusSerializer(data=request.data, context={"course": course})
#         if serializer.is_valid():
#             serializer.save()
#             return Response(serializer.data, status=status.HTTP_201_CREATED)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

#     def put(self, request, course_slug=None, version=None):
#         if version is None:
#             raise serializers.ValidationError("Missing syllabus version", code=400)
        
#         item = Syllabus.objects.filter(course__slug=course_slug, version=version).first()
#         if item is None:
#             raise serializers.ValidationError("Syllabus version not found", code=404)
        
#         serializer = SyllabusSerializer(item, data=request.data, many=False)
#         if serializer.is_valid():
#             serializer.save()
#             return Response(serializer.data, status=status.HTTP_201_CREATED)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
