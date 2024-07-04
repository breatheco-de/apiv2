import logging

from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from breathecode.admissions.models import CohortUser
from breathecode.authenticate.models import ProfileAcademy
from breathecode.utils import GenerateLookupsMixin, HeaderLimitOffsetPagination, capable_of
from breathecode.utils.api_view_extensions.api_view_extensions import APIViewExtensions
from breathecode.utils.decorators import has_permission
from breathecode.utils.find_by_full_name import query_like_by_full_name
from capyc.rest_framework.exceptions import ValidationException

from .actions import generate_certificate
from .models import Badge, LayoutDesign, Specialty, UserSpecialty
from .serializers import LayoutDesignSerializer, SpecialtySerializer, UserSpecialtySerializer
from .tasks import async_generate_certificate

logger = logging.getLogger(__name__)


@api_view(["GET"])
@permission_classes([AllowAny])
def get_specialties(request):
    items = Specialty.objects.all()
    serializer = SpecialtySerializer(items, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([AllowAny])
def get_badges(request):
    items = Badge.objects.all()
    serializer = SpecialtySerializer(items, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([AllowAny])
def get_certificate(request, token):
    item = UserSpecialty.objects.filter(token=token).first()
    if item is None:
        raise NotFound("Certificate not found")

    serializer = UserSpecialtySerializer(item)
    return Response(serializer.data, status=status.HTTP_200_OK)


class LayoutView(APIView):
    """
    List all snippets, or create a new snippet.
    """

    @capable_of("read_layout")
    def get(self, request, academy_id=None):

        layouts = LayoutDesign.objects.filter(academy__id=academy_id)

        serializer = LayoutDesignSerializer(layouts, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CertificateView(APIView):
    """
    List all snippets, or create a new snippet.
    """

    @capable_of("read_certificate")
    def get(self, request, cohort_id, student_id, academy_id=None):

        cert = UserSpecialty.objects.filter(
            cohort__id=cohort_id, user__id=student_id, cohort__academy__id=academy_id
        ).first()
        if cert is None:
            raise serializers.ValidationError("Certificate not found", code=404)

        serializer = UserSpecialtySerializer(cert, many=False)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @capable_of("crud_certificate")
    def post(self, request, cohort_id, student_id, academy_id=None):

        layout_slug = None

        if "layout_slug" in request.data:
            layout_slug = request.data["layout_slug"]

        cu = CohortUser.objects.filter(
            cohort__id=cohort_id, user__id=student_id, role="STUDENT", cohort__academy__id=academy_id
        ).first()

        if cu is None:
            raise ValidationException("Student not found for this cohort", code=404, slug="student-not-found")
        cert = generate_certificate(cu.user, cu.cohort, layout_slug)
        serializer = UserSpecialtySerializer(cert, many=False)

        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CertificateCohortView(APIView):
    """
    List all snippets, or create a new snippet.
    """

    @capable_of("read_certificate")
    def get(self, request, cohort_id, academy_id=None):

        cert = UserSpecialty.objects.filter(cohort__id=cohort_id, cohort__academy__id=academy_id).order_by(
            "-created_at"
        )
        serializer = UserSpecialtySerializer(cert, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @capable_of("crud_certificate")
    def post(self, request, cohort_id, academy_id=None):

        layout_slug = None
        if "layout_slug" in request.data:
            layout_slug = request.data["layout_slug"]

        cohort_users = CohortUser.objects.filter(cohort__id=cohort_id, role="STUDENT", cohort__academy__id=academy_id)
        all_certs = []
        cohort__users = []

        if cohort_users.count() == 0:
            raise ValidationException(
                "There are no users with STUDENT role in this cohort", code=400, slug="no-user-with-student-role"
            )

        for cohort_user in cohort_users:
            cohort = cohort_user.cohort
            if cohort.stage != "ENDED" or cohort.never_ends != False:
                raise ValidationException(
                    "Cohort stage must be ENDED or never ends", code=400, slug="cohort-stage-must-be-ended"
                )

            if not cohort.syllabus_version:
                raise ValidationException(
                    f"The cohort has no syllabus assigned, please set a syllabus for cohort: {cohort.name}",
                    slug="cohort-has-no-syllabus-version-assigned",
                )

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

    @capable_of("read_certificate")
    def get(self, request, academy_id=None):
        items = UserSpecialty.objects.filter(cohort__academy__id=academy_id)

        like = request.GET.get("like", None)
        if like is not None and like != "":
            items = query_like_by_full_name(like=like, items=items, prefix="user__")
            if items.count() == 0:
                items = UserSpecialty.objects.filter(cohort__academy__id=academy_id)
                items = query_like_by_full_name(like=like, items=items, prefix="user__profileacademy__")

        sort = request.GET.get("sort", None)
        if sort is None or sort == "":
            sort = "-created_at"

        items = items.order_by(sort)
        page = self.paginate_queryset(items, request)
        serializer = UserSpecialtySerializer(page, many=True)
        if self.is_paginate(request):
            return self.get_paginated_response(serializer.data)
        else:
            return Response(serializer.data, status=status.HTTP_200_OK)

    @capable_of("crud_certificate")
    def delete(self, request, cohort_id=None, user_id=None, academy_id=None):
        lookups = self.generate_lookups(request, many_fields=["id"])

        try:
            ids = lookups["id__in"]
        except Exception:
            raise ValidationException("User specialties ids were not provided", 404, slug="missing_ids")

        if lookups and (user_id or cohort_id):
            raise ValidationException(
                "user_id or cohort_id was provided in url " "in bulk mode request, use querystring style instead",
                code=400,
            )

        elif lookups:
            items = UserSpecialty.objects.filter(**lookups, academy__id=academy_id)

            if len(items) == 0:
                raise ValidationException(
                    f"No user specialties for deletion were found with following id: {','.join(ids)}",
                    code=404,
                    slug="specialties_not_found",
                )

            for item in items:
                item.delete()

            return Response(None, status=status.HTTP_204_NO_CONTENT)

    @capable_of("crud_certificate")
    def post(self, request, academy_id=None):
        data = request.data if isinstance(request.data, list) else [request.data]
        cohort_users = []

        if len(data) > 0:
            for items in data:
                cohort__slug = items.get("cohort_slug")
                user__id = items.get("user_id")
                cohort_user = CohortUser.objects.filter(
                    cohort__slug=cohort__slug, user_id=user__id, role="STUDENT", cohort__academy__id=academy_id
                ).first()

                if cohort_user is not None:
                    cohort_users.append(cohort_user)
                else:
                    student = ProfileAcademy.objects.filter(user_id=user__id).first()
                    if student is None:
                        raise ValidationException(f"User with id {str(user__id)} not found", 404)
                    raise ValidationException(
                        f"No student with id {str(student.first_name)} {str(student.last_name)} was found for cohort {str(cohort__slug)}",
                        code=404,
                        slug="student-not-found-in-cohort",
                    )
        else:
            raise ValidationException("You did not send anything to reattempts")

        certs = []
        for cu in cohort_users:
            cert = UserSpecialty.objects.filter(
                cohort__id=cu.cohort_id, user__id=cu.user_id, cohort__academy__id=academy_id
            ).first()
            if cert is not None:
                cert.status = "PENDING"
                cert.save()
                certs.append(cert)
            else:
                raise ValidationException(
                    "There is no certificate for this student and cohort", code=404, slug="no-user-specialty"
                )

            layout = cert.layout.slug if cert.layout is not None else "default"
            async_generate_certificate.delay(cu.cohort_id, cu.user_id, layout=layout)

        serializer = UserSpecialtySerializer(certs, many=True)

        return Response(serializer.data)


class CertificateMeView(APIView, HeaderLimitOffsetPagination, GenerateLookupsMixin):
    extensions = APIViewExtensions(sort="-created_at", paginate=True)

    @has_permission("get_my_certificate")
    def get(self, request):
        handler = self.extensions(request)

        items = UserSpecialty.objects.filter(user=request.user, status="PERSISTED")
        items = handler.queryset(items)
        serializer = UserSpecialtySerializer(items, many=True)

        return handler.response(serializer.data)
