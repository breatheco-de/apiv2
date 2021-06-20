import logging
from django.shortcuts import render
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Specialty, Badge, UserSpecialty
from django.db.models import Q
from breathecode.admissions.models import CohortUser
from breathecode.utils import capable_of, ValidationException, HeaderLimitOffsetPagination, APIException
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
def post_save_course_dosomething(sender, instance, **kwargs):
    if instance.preview_url is None or instance.preview_url == "" and instance.status == 'PERSISTED':
        take_screenshot.delay(instance.id)


class CertificateView(APIView):
    """
    List all snippets, or create a new snippet.
    """
    @capable_of('read_certificate')
    def get(self, request, cohort_id, student_id, academy_id=None):

        cert = UserSpecialty.objects.filter(
            cohort__id=cohort_id, user__id=student_id, cohort__academy__id=academy_id).first()
        if cert is None:
            raise serializers.ValidationError(
                "Certificate not found", code=404)

        serializer = UserSpecialtySerializer(cert, many=False)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @capable_of('crud_certificate')
    def post(self, request, cohort_id, student_id, academy_id=None):

        cu = CohortUser.objects.filter(
            cohort__id=cohort_id, user__id=student_id, role="STUDENT", cohort__academy__id=academy_id).first()
        if cu is None:
            raise serializers.ValidationError(
                f"Student not found for this cohort", code=404)

        cert = generate_certificate(cu.user, cu.cohort)
        serializer = UserSpecialtySerializer(cert, many=False)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CertificateCohortView(APIView):
    """
    List all snippets, or create a new snippet.
    """
    @capable_of('read_certificate')
    def get(self, request, cohort_id, academy_id=None):

        cert = UserSpecialty.objects.filter(
            cohort__id=cohort_id, cohort__academy__id=academy_id).order_by('-created_at')
        serializer = UserSpecialtySerializer(cert, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @capable_of('crud_certificate')
    def post(self, request, cohort_id, academy_id=None):

        cohort_users = CohortUser.objects.filter(
            cohort__id=cohort_id, role='STUDENT', cohort__academy__id=academy_id)
        all_certs = []
        cohort__users = []

        if cohort_users.count() == 0:
            raise ValidationException("There are no users with STUDENT role in this cohort", code=400, 
                slug="no-user-with-student-role")

        for cohort_user in cohort_users:
            cohort = cohort_user.cohort
            if cohort_user is None:
                raise ValidationException("Impossible to obtain the student cohort, maybe it's none assigned", code=400, 
                    slug="no-cohort-user-assigned")

            if cohort.stage != "ENDED" or cohort.never_ends != False:
                raise ValidationException("Cohort stage must be ENDED or never ends", code=400, 
                    slug="cohort-stage-must-be-ended")
            
            if cohort.syllabus is None: 
                raise ValidationException(f'The cohort has no syllabus assigned, please set a syllabus for cohort: {cohort.name}', code=400, 
                    slug="cohort-has-no-syllabus-assigned")
            
            if cohort.syllabus.certificate is None:
                raise ValidationException(f'The cohort has no certificate assigned, please set a certificate for cohort: {cohort.name}',
                    code=400, slug="cohort-has-no-certificate-assigned")
            
            if (not hasattr(cohort.syllabus.certificate, 'specialty') or not
                cohort.syllabus.certificate.specialty):
                raise ValidationException('Specialty has no certificate assigned, please set a '
                    f'certificate on the Specialty model: {cohort.syllabus.certificate.name}', code=400, 
                    slug="specialty-has-no-certificate-assigned")

            else:
                cohort__users.append(cohort_user)

        for cu in cohort__users:
            cert = generate_certificate(cu.user, cu.cohort)
            serializer = UserSpecialtySerializer(cert, many=False)
            all_certs.append(serializer.data)

        return Response(all_certs, status=status.HTTP_201_CREATED)


class CertificateAcademyView(APIView, HeaderLimitOffsetPagination):
    """
    List all snippets, or create a new snippet.
    """
    @capable_of('read_certificate')
    def get(self, request, academy_id=None):
        items = UserSpecialty.objects.filter(cohort__academy__id=academy_id)

        like = request.GET.get('like', None)
        if like is not None and like != "":
            for query in like.split():
                items = items.filter(Q(user__profileacademy__first_name__icontains=query) | Q(
                    user__profileacademy__last_name__icontains=query) | Q(user__first_name__icontains=query) | Q(
                    user__last_name__icontains=query) | Q(user__profileacademy__email__icontains=query) | Q(user__email__icontains=query))

        page = self.paginate_queryset(items, request)
        serializer = UserSpecialtySerializer(page, many=True)
        if self.is_paginate(request):
            return self.get_paginated_response(serializer.data)
        else:
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
