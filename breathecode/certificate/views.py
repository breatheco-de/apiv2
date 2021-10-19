from breathecode.authenticate.models import ProfileAcademy
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Specialty, Badge, UserSpecialty, LayoutDesign
from breathecode.admissions.models import CohortUser
from breathecode.utils import capable_of, ValidationException, HeaderLimitOffsetPagination, GenerateLookupsMixin
from .serializers import SpecialtySerializer, UserSpecialtySerializer, LayoutDesignSerializer
from rest_framework.exceptions import NotFound
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status, serializers
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from .tasks import take_screenshot, generate_one_certificate
from .actions import generate_certificate
from breathecode.utils.find_by_full_name import query_like_by_full_name

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
    if instance.preview_url is None or instance.preview_url == '' and instance.status == 'PERSISTED':
        take_screenshot.delay(instance.id)


class LayoutView(APIView):
    """
    List all snippets, or create a new snippet.
    """
    @capable_of('read_layout')
    def get(self, request, academy_id=None):

        layouts = LayoutDesign.objects.filter(academy__id=academy_id)

        serializer = LayoutDesignSerializer(layouts, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CertificateView(APIView):
    """
    List all snippets, or create a new snippet.
    """
    @capable_of('read_certificate')
    def get(self, request, cohort_id, student_id, academy_id=None):

        cert = UserSpecialty.objects.filter(cohort__id=cohort_id,
                                            user__id=student_id,
                                            cohort__academy__id=academy_id).first()
        if cert is None:
            raise serializers.ValidationError('Certificate not found', code=404)

        serializer = UserSpecialtySerializer(cert, many=False)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @capable_of('crud_certificate')
    def post(self, request, cohort_id, student_id, academy_id=None):

        layout_slug = None

        if 'layout_slug' in request.data:
            layout_slug = request.data['layout_slug']

        cu = CohortUser.objects.filter(cohort__id=cohort_id,
                                       user__id=student_id,
                                       role='STUDENT',
                                       cohort__academy__id=academy_id).first()

        if cu is None:
            raise ValidationException('Student not found for this cohort', code=404, slug='student-not-found')

        cert = generate_certificate(cu.user, cu.cohort, layout_slug)
        serializer = UserSpecialtySerializer(cert, many=False)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CertificateCohortView(APIView):
    """
    List all snippets, or create a new snippet.
    """
    @capable_of('read_certificate')
    def get(self, request, cohort_id, academy_id=None):

        cert = UserSpecialty.objects.filter(cohort__id=cohort_id,
                                            cohort__academy__id=academy_id).order_by('-created_at')
        serializer = UserSpecialtySerializer(cert, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @capable_of('crud_certificate')
    def post(self, request, cohort_id, academy_id=None):

        layout_slug = None
        if 'layout_slug' in request.data:
            layout_slug = request.data['layout_slug']

        cohort_users = CohortUser.objects.filter(cohort__id=cohort_id,
                                                 role='STUDENT',
                                                 cohort__academy__id=academy_id)
        all_certs = []
        cohort__users = []

        if cohort_users.count() == 0:
            raise ValidationException('There are no users with STUDENT role in this cohort',
                                      code=400,
                                      slug='no-user-with-student-role')

        for cohort_user in cohort_users:
            cohort = cohort_user.cohort
            if cohort.stage != 'ENDED' or cohort.never_ends != False:
                raise ValidationException('Cohort stage must be ENDED or never ends',
                                          code=400,
                                          slug='cohort-stage-must-be-ended')

            if not cohort.syllabus_version:
                raise ValidationException(
                    f'The cohort has no syllabus assigned, please set a syllabus for cohort: {cohort.name}',
                    slug='cohort-has-no-syllabus-version-assigned')

            else:
                cohort__users.append(cohort_user)

        for cu in cohort__users:
            cert = generate_certificate(cu.user, cu.cohort, layout_slug)
            serializer = UserSpecialtySerializer(cert, many=False)
            all_certs.append(serializer.data)

        return Response(all_certs, status=status.HTTP_201_CREATED)


class CertificateAcademyView(APIView, HeaderLimitOffsetPagination, GenerateLookupsMixin):
    """
    List all snippets, or create a new snippet.
    """
    @capable_of('read_certificate')
    def get(self, request, academy_id=None):
        items = UserSpecialty.objects.filter(cohort__academy__id=academy_id)

        like = request.GET.get('like', None)
        if like is not None and like != '':
            items = query_like_by_full_name(like=like, items=items, prefix='user__')
            if items.count() == 0:
                items = UserSpecialty.objects.filter(cohort__academy__id=academy_id)
                items = query_like_by_full_name(like=like, items=items, prefix='user__profileacademy__')

        sort = request.GET.get('sort', None)
        if sort is None or sort == '':
            sort = '-created_at'

        items = items.order_by(sort)
        page = self.paginate_queryset(items, request)
        serializer = UserSpecialtySerializer(page, many=True)
        if self.is_paginate(request):
            return self.get_paginated_response(serializer.data)
        else:
            return Response(serializer.data, status=status.HTTP_200_OK)

    @capable_of('crud_certificate')
    def delete(self, request, cohort_id=None, user_id=None, academy_id=None):
        lookups = self.generate_lookups(request, many_fields=['id'])

        try:
            ids = lookups['id__in']
        except:
            raise ValidationException('User specialties ids were not provided', 404, slug='missing_ids')

        if lookups and (user_id or cohort_id):
            raise ValidationException(
                'user_id or cohort_id was provided in url '
                'in bulk mode request, use querystring style instead',
                code=400)

        elif lookups:
            items = UserSpecialty.objects.filter(**lookups, academy__id=academy_id)

            if len(items) == 0:
                raise ValidationException(
                    f"No user specialties for deletion were found with following id: {','.join(ids)}",
                    code=404,
                    slug='specialties_not_found')

            for item in items:
                item.delete()

            return Response(None, status=status.HTTP_204_NO_CONTENT)

    @capable_of('crud_certificate')
    def post(self, request, academy_id=None):
        if isinstance(request.data, list):
            data = request.data

        else:
            data = [request.data]

        cohort_users = []

        if len(data) > 0:
            for items in data:
                cohort__slug = items.get('cohort_slug')
                user__id = items.get('user_id')
                cohort_user = CohortUser.objects.filter(cohort__slug=cohort__slug,
                                                        user_id=user__id,
                                                        role='STUDENT',
                                                        cohort__academy__id=academy_id).first()

                if cohort_user is not None:
                    cohort_users.append(cohort_user)
                else:
                    student = ProfileAcademy.objects.filter(user_id=user__id).first()
                    if student is None:
                        raise ValidationException(f'User with id {str(user__id)} not found', 404)
                    raise ValidationException(
                        f'No student with id {str(student.first_name)} {str(student.last_name)} was found for cohort {str(cohort__slug)}',
                        code=404,
                        slug='student-not-found-in-cohort')
        else:
            raise ValidationException('You did not send anything to reattemps')

        certs = []
        for cu in cohort_users:
            cert = UserSpecialty.objects.filter(cohort__id=cu.cohort_id,
                                                user__id=cu.user_id,
                                                cohort__academy__id=academy_id).first()
            if cert is not None:
                cert.status = 'PENDING'
                cert.save()
                certs.append(cert)
            else:
                raise ValidationException('There is no certificate for this student and cohort',
                                          code=404,
                                          slug='no-user-specialty')
            generate_one_certificate.delay(cu.cohort_id, cu.user_id, layout='default')

        serializer = UserSpecialtySerializer(certs, many=True)

        return Response(serializer.data)


# class CertificateSyllabusVersionView(APIView):
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

#         serializer = GetSyllabusVersionSerializer(syl, many=False)
#         return Response(serializer.data, status=status.HTTP_200_OK)
#     def post(self, request, course_slug=None):
#         version = 1
#         course = Course.objects.filter(slug=course_slug).first()
#         if course is None:
#             raise serializers.ValidationError(f"Invalid course slug {course__slug}", code=404)

#         item = Syllabus.objects.filter(course__slug=course_slug).order_by('version').first()

#         if item is not None:
#             version = item.version + 1

#         serializer = SyllabusVersionSerializer(data=request.data, context={"course": course})
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

#         serializer = SyllabusVersionSerializer(item, data=request.data, many=False)
#         if serializer.is_valid():
#             serializer.save()
#             return Response(serializer.data, status=status.HTTP_201_CREATED)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
