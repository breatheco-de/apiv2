import logging

from capyc.rest_framework.exceptions import ValidationException
from capyc.core.i18n import translation
from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from breathecode.admissions.diagnostics import build_graduation_diagnostic
from breathecode.admissions.models import Academy, CERTIFICATE_RECIPIENT_ROLES, Cohort, CohortUser, Syllabus
from breathecode.authenticate.models import ProfileAcademy, User
from breathecode.authenticate.actions import get_user_language
from breathecode.utils import GenerateLookupsMixin, HeaderLimitOffsetPagination, capable_of
from breathecode.utils.api_view_extensions.api_view_extensions import APIViewExtensions
from breathecode.utils.api_view_extensions.extensions.lookup_extension import Q
from breathecode.utils.decorators import has_permission
from breathecode.utils.find_by_full_name import query_like_by_full_name

from .actions import (
    generate_certificate,
    generate_certificate_ignoring_tasks,
    get_syllabus_specialty_bucket_conflict,
)
from .diagnostics import build_certificate_diagnostic, list_graduated_without_certificate_cohort_users
from .models import Badge, LayoutDesign, Specialty, UserSpecialty
from .serializers import BadgeSerializer, LayoutDesignSerializer, SpecialtySerializer, UserSpecialtySerializer
from .tasks import async_generate_certificate

logger = logging.getLogger(__name__)


def _parse_request_bool(value) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("true", "1", "yes")
    return bool(value)


def _specialty_visible_to_academy_q(academy_id):
    """Global specialties (no academy) or owned by this academy; never another academy's."""
    return Q(academy__isnull=True) | Q(academy_id=academy_id)


class AcademySpecialtiesView(APIView, GenerateLookupsMixin):
    """List academy specialties with pagination and filtering."""

    permission_classes = [AllowAny]
    extensions = APIViewExtensions(paginate=True)

    @capable_of("read_certificate")
    def get(self, request, academy_id=None):
        handler = self.extensions(request)

        # Global specialties (no academy) apply to every academy; also include
        # specialties owned by this academy. Never another academy's.
        items = (
            Specialty.objects.filter(_specialty_visible_to_academy_q(academy_id))
            .exclude(status=Specialty.DELETED)
            .distinct()
        )

        like = request.GET.get("like")
        if like:
            items = items.filter(Q(name__icontains=like) | Q(syllabuses__name__icontains=like))

        syllabus_slug = request.GET.get("syllabus_slug")
        if syllabus_slug:
            items = items.filter(syllabuses__slug=syllabus_slug).distinct()

        # Custom sorting: by number of graduates (total_issued from metrics), then alphabetically
        # Use JSON field operations to extract total_issued from metrics
        items = items.extra(
            select={
                'total_issued': "COALESCE((metrics->>'total_issued')::integer, 0)"
            }
        ).order_by('-total_issued', 'name')

        items = handler.queryset(items)
        serializer = SpecialtySerializer(items, many=True)

        return handler.response(serializer.data)

    @capable_of("crud_certificate")
    def post(self, request, academy_id=None):
        data = request.data or {}
        name = data.get("name")
        slug = data.get("slug")
        lang = get_user_language(request)
        if not name or not slug:
            raise ValidationException(
                translation(
                    lang,
                    en="name and slug are required",
                    es="name y slug son requeridos",
                ),
                code=400,
                slug="missing-fields",
            )
        if Specialty.objects.filter(slug=slug).exists():
            raise ValidationException(
                translation(
                    lang,
                    en=f"Specialty with slug '{slug}' already exists",
                    es=f"Ya existe una especialidad con slug '{slug}'",
                ),
                code=400,
                slug="specialty-slug-already-exists",
            )
        academy = Academy.objects.filter(id=academy_id).first()
        if not academy:
            raise ValidationException(
                translation(
                    lang,
                    en="Academy not found",
                    es="Academia no encontrada",
                ),
                code=404,
                slug="academy-not-found",
            )
        specialty = Specialty(
            name=name,
            slug=slug,
            academy_id=academy_id,
            description=data.get("description") or None,
            logo_url=data.get("logo_url") or None,
            duration_in_hours=data.get("duration_in_hours"),
            expiration_day_delta=data.get("expiration_day_delta"),
            status=data.get("status", Specialty.ACTIVE),
        )
        specialty.save()
        serializer = SpecialtySerializer(specialty, many=False)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class AcademySpecialtyByIdView(APIView):
    """Get or update a single academy-owned specialty."""

    permission_classes = [AllowAny]

    @capable_of("read_certificate")
    def get(self, request, specialty_id, academy_id=None):
        specialty = (
            Specialty.objects.filter(Q(id=specialty_id) & _specialty_visible_to_academy_q(academy_id))
            .exclude(status=Specialty.DELETED)
            .distinct()
            .first()
        )
        if not specialty:
            raise NotFound("Specialty not found")
        serializer = SpecialtySerializer(specialty, many=False)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @capable_of("crud_certificate")
    def put(self, request, specialty_id, academy_id=None):
        return self._update(request, specialty_id, academy_id, partial=False)

    @capable_of("crud_certificate")
    def patch(self, request, specialty_id, academy_id=None):
        return self._update(request, specialty_id, academy_id, partial=True)

    def _update(self, request, specialty_id, academy_id, partial):
        specialty = Specialty.objects.filter(id=specialty_id).first()
        if not specialty:
            raise NotFound("Specialty not found")
        lang = get_user_language(request)
        if specialty.academy_id is None or specialty.academy_id != academy_id:
            raise ValidationException(
                translation(
                    lang,
                    en="You can only update specialties that belong to your academy",
                    es="Solo puedes actualizar especialidades que pertenecen a tu academia",
                ),
                code=403,
                slug="academy-cannot-update-this-specialty",
            )
        data = request.data or {}
        allowed = {
            "name",
            "slug",
            "description",
            "logo_url",
            "duration_in_hours",
            "expiration_day_delta",
            "status",
        }
        for key in allowed:
            if key in data:
                setattr(specialty, key, data[key])
        specialty.save()
        serializer = SpecialtySerializer(specialty, many=False)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AcademySpecialtySyllabusView(APIView):
    """Link a syllabus to a specialty (add to syllabuses ManyToMany)."""

    permission_classes = [AllowAny]

    @capable_of("crud_syllabus")
    def post(self, request, specialty_id, academy_id=None):
        specialty = (
            Specialty.objects.filter(Q(id=specialty_id) & _specialty_visible_to_academy_q(academy_id))
            .exclude(status=Specialty.DELETED)
            .distinct()
            .first()
        )
        if not specialty:
            raise NotFound("Specialty not found")
        data = request.data or {}
        syllabus_id = data.get("syllabus_id")
        syllabus_slug = data.get("syllabus_slug")
        lang = get_user_language(request)
        if not syllabus_id and not syllabus_slug:
            raise ValidationException(
                translation(
                    lang,
                    en="syllabus_id or syllabus_slug is required",
                    es="syllabus_id o syllabus_slug es requerido",
                ),
                code=400,
                slug="missing-syllabus-identifier",
            )
        syllabus = None
        if syllabus_id:
            syllabus = Syllabus.objects.filter(id=syllabus_id).first()
        if syllabus is None and syllabus_slug:
            syllabus = Syllabus.objects.filter(slug=syllabus_slug).first()
        if not syllabus:
            raise ValidationException(
                translation(
                    lang,
                    en="Syllabus not found",
                    es="Syllabus no encontrado",
                ),
                code=404,
                slug="syllabus-not-found",
            )
        if specialty.syllabuses.filter(pk=syllabus.pk).exists():
            # Idempotent: already linked
            serializer = SpecialtySerializer(specialty, many=False)
            return Response(serializer.data, status=status.HTTP_200_OK)
        conflict = get_syllabus_specialty_bucket_conflict(specialty, syllabus)
        if conflict:
            raise ValidationException(
                translation(
                    lang,
                    en=f"Another specialty already uses this syllabus for this scope (specialty id={conflict.slug}).",
                    es="Otra especialidad ya usa este syllabus en este ámbito.",
                ),
                code=400,
                slug="syllabus-specialty-already-linked",
            )
        specialty.syllabuses.add(syllabus)
        serializer = SpecialtySerializer(specialty, many=False)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class BadgesView(APIView, GenerateLookupsMixin):
    """List badges with pagination and filtering."""

    permission_classes = [AllowAny]
    extensions = APIViewExtensions(sort="-created_at", paginate=True)

    def get(self, request):
        handler = self.extensions(request)

        items = Badge.objects.all()
        
        # Add filtering by specialty if provided
        specialty_slug = request.GET.get("specialty_slug")
        if specialty_slug:
            items = items.filter(specialties__slug=specialty_slug).distinct()
        
        # Add search functionality
        like = request.GET.get("like")
        if like:
            items = items.filter(Q(name__icontains=like) | Q(slug__icontains=like))
        
        items = handler.queryset(items)
        serializer = BadgeSerializer(items, many=True)

        return handler.response(serializer.data)


@api_view(["GET"])
@permission_classes([AllowAny])
def get_certificate(request, token):
    item = UserSpecialty.objects.filter(token=token).first()
    if item is None:
        raise NotFound("Certificate not found")

    lang = get_user_language(request)
    cohort_user = CohortUser.objects.filter(
        cohort__id=item.cohort.id, user__id=item.user.id, role__in=CERTIFICATE_RECIPIENT_ROLES
    ).first()
    if cohort_user is None:
        raise ValidationException(
            translation(
                lang,
                en="Certificate is not valid because no record of this user was found with an eligible role in this cohort",
                es="Este certificado no es válido porque no se encontró ningún registro de este usuario con un rol elegible en esta cohorte",
                slug="certificate-not-valid",
            ),
            code=400,
        )

    if cohort_user.finantial_status == "LATE":
        raise ValidationException(
            translation(
                lang,
                en="This certificate has been revoked and its no longer valid. Contact your Program Manager if you think this is an error.",
                es="Este certificado ha sido revocado y ya no es válido. Contacta a tu Program Manager si crees que esto es un error.",
                slug="revoked-certificate",
            ),
            code=400,
        )
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
            cohort__id=cohort_id,
            user__id=student_id,
            role__in=CERTIFICATE_RECIPIENT_ROLES,
            cohort__academy__id=academy_id,
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
        lang = get_user_language(request)
        layout_slug = request.data.get("layout_slug")
        ignore_tasks = _parse_request_bool(request.data.get("ignore_tasks"))
        student_id = request.data.get("student_id")

        if student_id is not None:
            try:
                student_id = int(student_id)
            except (TypeError, ValueError):
                raise ValidationException(
                    translation(lang, en="student_id must be an integer", es="student_id debe ser un entero"),
                    code=400,
                    slug="invalid-student-id",
                )

        cohort_users = CohortUser.objects.filter(
            cohort__id=cohort_id, role__in=CERTIFICATE_RECIPIENT_ROLES, cohort__academy__id=academy_id
        )

        if student_id is not None:
            cohort_users = cohort_users.filter(user__id=student_id)

        if cohort_users.count() == 0:
            if student_id is not None:
                raise ValidationException(
                    translation(
                        lang,
                        en="Student not found for this cohort",
                        es="Estudiante no encontrado en este cohort",
                    ),
                    code=404,
                    slug="student-not-found",
                )
            raise ValidationException(
                "There are no users with an eligible role (STUDENT, TEACHER, ASSISTANT, or REVIEWER) in this cohort",
                code=400,
                slug="no-user-with-student-role",
            )

        cohort__users = []
        for cohort_user in cohort_users:
            cohort = cohort_user.cohort
            if not cohort.never_ends and cohort.stage != "ENDED":
                raise ValidationException(
                    "Cohort stage must be ENDED or never ends", code=400, slug="cohort-stage-must-be-ended"
                )

            if not cohort.syllabus_version:
                raise ValidationException(
                    f"The cohort has no syllabus assigned, please set a syllabus for cohort: {cohort.name}",
                    slug="cohort-has-no-syllabus-version-assigned",
                )

            cohort__users.append(cohort_user)

        generate_fn = generate_certificate_ignoring_tasks if ignore_tasks else generate_certificate
        all_certs = []

        for cu in cohort__users:
            cert = generate_fn(cu.user, cu.cohort, layout_slug)
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

        # Filter by user_id if provided
        user_id = request.GET.get("user_id", None)
        if user_id is not None and user_id != "":
            try:
                user_id = int(user_id)
                items = items.filter(user__id=user_id)
            except (ValueError, TypeError):
                raise ValidationException(
                    "user_id must be a valid integer", code=400, slug="invalid-user-id"
                )

        like = request.GET.get("like", None)
        if like is not None and like != "":
            items = query_like_by_full_name(like=like, items=items, prefix="user__")
            if items.count() == 0:
                items = UserSpecialty.objects.filter(cohort__academy__id=academy_id)
                if user_id is not None:
                    items = items.filter(user__id=user_id)
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
                    cohort__slug=cohort__slug,
                    user_id=user__id,
                    role__in=CERTIFICATE_RECIPIENT_ROLES,
                    cohort__academy__id=academy_id,
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


class AcademyStudentDiagnosticView(APIView):
    """
    Read-only graduation or certificate diagnostics for students (same rules as diagnose_* commands).
    Required query: kind=graduation|certificate.
    Targeting: cohort_user_id; or user_id / user_email with optional cohort_id;
    or scope=cohort&cohort_id; or all_graduated_without_certificate=true (certificate only).
    """

    @capable_of("read_certificate")
    def get(self, request, academy_id=None):
        lang = get_user_language(request)
        kind = request.GET.get("kind")
        if kind not in ("graduation", "certificate"):
            raise ValidationException(
                translation(
                    lang,
                    en="kind must be graduation or certificate",
                    es="kind debe ser graduation o certificate",
                ),
                code=400,
                slug="invalid-diagnostic-kind",
            )

        ag_flag = request.GET.get("all_graduated_without_certificate", "").lower() in ("true", "1", "yes")
        if ag_flag:
            if kind != "certificate":
                raise ValidationException(
                    translation(
                        lang,
                        en="all_graduated_without_certificate only applies when kind=certificate",
                        es="all_graduated_without_certificate solo aplica cuando kind=certificate",
                    ),
                    code=400,
                    slug="invalid-diagnostic-combination",
                )
            try:
                limit = int(request.GET.get("limit") or 20)
            except (TypeError, ValueError):
                raise ValidationException(
                    translation(lang, en="limit must be an integer", es="limit debe ser un entero"),
                    code=400,
                    slug="invalid-limit",
                )
            if limit < 1 or limit > 500:
                raise ValidationException(
                    translation(lang, en="limit must be between 1 and 500", es="limit debe estar entre 1 y 500"),
                    code=400,
                    slug="invalid-limit",
                )
            cohort_users = list_graduated_without_certificate_cohort_users(academy_id, limit)
            results = [build_certificate_diagnostic(cu) for cu in cohort_users]
            return Response(
                {"kind": "certificate", "academy_id": academy_id, "results": results},
                status=status.HTTP_200_OK,
            )

        scope = request.GET.get("scope")
        if scope == "cohort":
            cohort_id_raw = request.GET.get("cohort_id")
            if not cohort_id_raw:
                raise ValidationException(
                    translation(
                        lang,
                        en="cohort_id is required when scope=cohort",
                        es="cohort_id es requerido cuando scope=cohort",
                    ),
                    code=400,
                    slug="missing-cohort-id",
                )
            try:
                cohort_id = int(cohort_id_raw)
            except (TypeError, ValueError):
                raise ValidationException(
                    translation(lang, en="cohort_id must be an integer", es="cohort_id debe ser un entero"),
                    code=400,
                    slug="invalid-cohort-id",
                )
            cohort = Cohort.objects.filter(id=cohort_id).first()
            if cohort is None or cohort.academy_id != academy_id:
                raise ValidationException(
                    translation(
                        lang,
                        en="Cohort not found for this academy",
                        es="Cohorte no encontrada para esta academia",
                    ),
                    code=404,
                    slug="cohort-not-found",
                )
            try:
                limit = int(request.GET.get("limit") or 50)
                offset = int(request.GET.get("offset") or 0)
            except (TypeError, ValueError):
                raise ValidationException(
                    translation(lang, en="limit and offset must be integers", es="limit y offset deben ser enteros"),
                    code=400,
                    slug="invalid-pagination",
                )
            if limit < 1 or limit > 500 or offset < 0:
                raise ValidationException(
                    translation(lang, en="Invalid limit or offset", es="limit u offset inválido"),
                    code=400,
                    slug="invalid-pagination",
                )
            qs = (
                CohortUser.objects.filter(cohort_id=cohort_id, role__in=CERTIFICATE_RECIPIENT_ROLES)
                .exclude(cohort__stage="DELETED")
                .order_by("id")[offset : offset + limit]
            )
            results = []
            for cu in qs:
                if kind == "graduation":
                    results.append(build_graduation_diagnostic(cu))
                else:
                    results.append(build_certificate_diagnostic(cu))
            return Response({"kind": kind, "academy_id": academy_id, "results": results}, status=status.HTTP_200_OK)

        cohort_user_id = request.GET.get("cohort_user_id")
        user_id = request.GET.get("user_id")
        user_email = request.GET.get("user_email")
        cohort_id_filter = request.GET.get("cohort_id")

        if cohort_user_id:
            try:
                cu_id = int(cohort_user_id)
            except (TypeError, ValueError):
                raise ValidationException(
                    translation(lang, en="cohort_user_id must be an integer", es="cohort_user_id debe ser un entero"),
                    code=400,
                    slug="invalid-cohort-user-id",
                )
            cohort_user = CohortUser.objects.exclude(cohort__stage="DELETED").filter(id=cu_id).first()
            if cohort_user is None:
                raise ValidationException(
                    translation(lang, en="CohortUser not found", es="CohortUser no encontrado"),
                    code=404,
                    slug="cohort-user-not-found",
                )
            if cohort_user.cohort.academy_id != academy_id:
                raise ValidationException(
                    translation(
                        lang,
                        en="CohortUser not found for this academy",
                        es="CohortUser no encontrado para esta academia",
                    ),
                    code=404,
                    slug="cohort-user-not-found",
                )
            if kind == "graduation":
                result = build_graduation_diagnostic(cohort_user)
            else:
                result = build_certificate_diagnostic(cohort_user)
            return Response({"kind": kind, "academy_id": academy_id, "result": result}, status=status.HTTP_200_OK)

        if user_id or user_email:
            if user_id:
                try:
                    uid = int(user_id)
                except (TypeError, ValueError):
                    raise ValidationException(
                        translation(lang, en="user_id must be an integer", es="user_id debe ser un entero"),
                        code=400,
                        slug="invalid-user-id",
                    )
                user = User.objects.filter(id=uid).first()
            else:
                user = User.objects.filter(email=user_email.strip()).first()
            if user is None:
                raise ValidationException(
                    translation(lang, en="User not found", es="Usuario no encontrado"),
                    code=404,
                    slug="user-not-found",
                )
            q = {"user__id": user.id}
            if cohort_id_filter:
                try:
                    q["cohort__id"] = int(cohort_id_filter)
                except (TypeError, ValueError):
                    raise ValidationException(
                        translation(lang, en="cohort_id must be an integer", es="cohort_id debe ser un entero"),
                        code=400,
                        slug="invalid-cohort-id",
                    )
            cohort_users = list(CohortUser.objects.filter(**q).exclude(cohort__stage="DELETED"))
            if not cohort_users:
                raise ValidationException(
                    translation(
                        lang,
                        en="No CohortUser found for this user",
                        es="No hay CohortUser para este usuario",
                    ),
                    code=404,
                    slug="cohort-user-not-found",
                )
            if len(cohort_users) > 1 and not cohort_id_filter:
                raise ValidationException(
                    translation(
                        lang,
                        en="User is in multiple cohorts; pass cohort_id to choose one",
                        es="El usuario está en varias cohortes; envía cohort_id para elegir una",
                    ),
                    code=400,
                    slug="ambiguous-cohort-user",
                )
            out = []
            for cu in cohort_users:
                if cu.cohort.academy_id != academy_id:
                    raise ValidationException(
                        translation(
                            lang,
                            en="CohortUser not found for this academy",
                            es="CohortUser no encontrado para esta academia",
                        ),
                        code=404,
                        slug="cohort-user-not-found",
                    )
                if kind == "graduation":
                    out.append(build_graduation_diagnostic(cu))
                else:
                    out.append(build_certificate_diagnostic(cu))
            if len(out) == 1:
                return Response({"kind": kind, "academy_id": academy_id, "result": out[0]}, status=status.HTTP_200_OK)
            return Response({"kind": kind, "academy_id": academy_id, "results": out}, status=status.HTTP_200_OK)

        raise ValidationException(
            translation(
                lang,
                en="Provide cohort_user_id, user_id or user_email, scope=cohort with cohort_id, or all_graduated_without_certificate",
                es="Indique cohort_user_id, user_id o user_email, scope=cohort con cohort_id, o all_graduated_without_certificate",
            ),
            code=400,
            slug="missing-diagnostic-target",
        )


class CertificateMeView(APIView, HeaderLimitOffsetPagination, GenerateLookupsMixin):
    extensions = APIViewExtensions(sort="-created_at", paginate=True)

    @has_permission("get_my_certificate")
    def get(self, request):
        handler = self.extensions(request)

        items = UserSpecialty.objects.filter(user=request.user, status="PERSISTED")
        items = handler.queryset(items)
        serializer = UserSpecialtySerializer(items, many=True)

        return handler.response(serializer.data)
