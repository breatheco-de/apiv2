from capyc.core.i18n import translation
from capyc.rest_framework.exceptions import ValidationException
from django.db import IntegrityError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from slugify import slugify

from breathecode.authenticate.actions import get_user_language
from breathecode.utils import GenerateLookupsMixin, capable_of
from breathecode.utils.api_view_extensions.api_view_extensions import APIViewExtensions
from breathecode.utils.decorators.has_permission import validate_permission

from .models import (
    CareerPath,
    CareerStage,
    Competency,
    CompetencySkill,
    JobFamily,
    JobRole,
    Skill,
    SkillAttitudeTag,
    SkillDomain,
    SkillKnowledgeItem,
    StageCompetency,
    StageSkill,
)
from .serializers import (
    CareerPathSerializer,
    CareerPathWithStagesSerializer,
    CareerStageCreateSerializer,
    CareerStageListSerializer,
    CareerStageSmallSerializer,
    CompetencyDetailSerializer,
    CompetencySerializer,
    GetJobFamilySerializer,
    GetJobRoleSerializer,
    JobFamilySerializer,
    JobRoleSerializer,
    JobRoleWithCareerPathsSerializer,
    SkillAttitudeTagSerializer,
    SkillDetailSerializer,
    SkillDomainSerializer,
    SkillDomainWriteSerializer,
    SkillKnowledgeItemSerializer,
    SkillSerializer,
    StageAssignmentSerializer,
    StageSkillCreateSerializer,
)


def apply_academy_filter(queryset, request, academy_id, academy_field="academy"):
    """
    Apply academy filtering to queryset.
    
    By default, includes models where academy IS NULL or academy matches academy_id.
    If 'academy=self' is in query string, only shows models for the specific academy.
    
    Args:
        queryset: Django QuerySet to filter
        request: HTTP request object (for query string access)
        academy_id: Academy ID from URL parameter (can be None)
        academy_field: Field name for academy relationship (default: "academy")
    
    Returns:
        Filtered QuerySet
    """
    from django.db.models import Q
    
    academy_self = request.GET.get("academy") == "self"
    
    if academy_self and academy_id:
        # Only show models for this specific academy (exclude null)
        return queryset.filter(**{f"{academy_field}__id": academy_id})
    elif academy_id:
        # Show models where academy IS NULL OR academy matches academy_id
        return queryset.filter(
            Q(**{f"{academy_field}__isnull": True}) | Q(**{f"{academy_field}__id": academy_id})
        )
    else:
        # No academy_id in URL, show all (including academy IS NULL and all academies)
        # But if academy=self is specified without academy_id, show nothing
        if academy_self:
            return queryset.none()
        return queryset


def assert_mutable_career_path(request, lang, career_path, academy_id):
    """Enforce global vs academy-owned rules for mutating a CareerPath (and nested stages)."""
    if career_path.academy is None:
        if not validate_permission(request.user, "crud_career_path"):
            raise ValidationException(
                translation(
                    lang,
                    en="Only users with crud_career_path permission can modify global career paths",
                    es="Solo usuarios con permiso crud_career_path pueden modificar trayectorias globales",
                    slug="no-permission-for-global",
                ),
                code=403,
            )
    elif academy_id and career_path.academy and career_path.academy.id != int(academy_id):
        raise ValidationException(
            translation(
                lang,
                en="Career path belongs to a different academy",
                es="La trayectoria pertenece a otra academia",
                slug="academy-mismatch",
            ),
            code=403,
        )


def get_career_path_or_404(lang, career_path_id):
    try:
        return CareerPath.objects.select_related("academy", "job_role", "job_role__job_family").get(id=career_path_id)
    except CareerPath.DoesNotExist:
        raise ValidationException(
            translation(lang, en="Career path not found", es="Trayectoria no encontrada", slug="not-found"),
            code=404,
        )


def assert_job_role_visible_for_academy(request, lang, job_role, academy_id):
    """Job role must be visible under apply_academy_filter for this academy."""
    visible = apply_academy_filter(JobRole.objects.filter(id=job_role.id), request, academy_id)
    if not visible.exists():
        raise ValidationException(
            translation(lang, en="Job role not found", es="Rol de trabajo no encontrado", slug="not-found"),
            code=404,
        )


class JobFamilyView(APIView, GenerateLookupsMixin):
    """
    List all job families or create a new job family.
    """

    extensions = APIViewExtensions(sort="name", paginate=True)

    @capable_of("read_career_path")
    def get(self, request, academy_id=None):
        handler = self.extensions(request)
        lang = get_user_language(request)

        items = JobFamily.objects.filter()
        items = apply_academy_filter(items, request, academy_id)

        items = handler.queryset(items)
        serializer = GetJobFamilySerializer(items, many=True)

        return handler.response(serializer.data)

    @capable_of("crud_career_path")
    def post(self, request, academy_id=None):
        lang = get_user_language(request)

        data = {**request.data}

        # Set academy from URL parameter if provided
        if academy_id and "academy" not in data:
            data["academy"] = academy_id

        serializer = JobFamilySerializer(data=data, many=False)
        if serializer.is_valid():
            serializer.save()
            job_family = serializer.instance
            response_serializer = GetJobFamilySerializer(job_family, many=False)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class JobFamilyByIdView(APIView):
    """
    Get, update, or delete a job family by id.
    """

    @capable_of("read_career_path")
    def get(self, request, job_family_id=None, academy_id=None):
        lang = get_user_language(request)

        item = JobFamily.objects.filter(id=job_family_id)
        item = apply_academy_filter(item, request, academy_id)

        item = item.first()

        if not item:
            raise ValidationException(
                translation(lang, en="Job family not found", es="Familia de trabajo no encontrada", slug="not-found"),
                code=404,
            )

        serializer = GetJobFamilySerializer(item, many=False)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @capable_of("crud_career_path")
    def put(self, request, job_family_id=None, academy_id=None):
        lang = get_user_language(request)

        try:
            item = JobFamily.objects.get(id=job_family_id)
        except JobFamily.DoesNotExist:
            raise ValidationException(
                translation(lang, en="Job family not found", es="Familia de trabajo no encontrada", slug="not-found"),
                code=404,
            )

        # If academy is None, only allow users with crud_career_path permission
        if item.academy is None:
            if not validate_permission(request.user, "crud_career_path"):
                raise ValidationException(
                    translation(
                        lang,
                        en="Only users with crud_career_path permission can modify global job families",
                        es="Solo usuarios con permiso crud_career_path pueden modificar familias de trabajo globales",
                        slug="no-permission-for-global",
                    ),
                    code=403,
                )

        # If academy is set, ensure it matches the academy_id from URL
        elif academy_id and item.academy and item.academy.id != int(academy_id):
            raise ValidationException(
                translation(
                    lang,
                    en="Job family belongs to a different academy",
                    es="La familia de trabajo pertenece a otra academia",
                    slug="academy-mismatch",
                ),
                code=403,
            )

        serializer = JobFamilySerializer(item, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            # Return full data with GET serializer
            job_family = JobFamily.objects.get(id=item.id)
            response_serializer = GetJobFamilySerializer(job_family, many=False)
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of("crud_career_path")
    def delete(self, request, job_family_id=None, academy_id=None):
        lang = get_user_language(request)

        try:
            item = JobFamily.objects.get(id=job_family_id)
        except JobFamily.DoesNotExist:
            raise ValidationException(
                translation(lang, en="Job family not found", es="Familia de trabajo no encontrada", slug="not-found"),
                code=404,
            )

        # If academy is None, only allow users with crud_career_path permission
        if item.academy is None:
            if not validate_permission(request.user, "crud_career_path"):
                raise ValidationException(
                    translation(
                        lang,
                        en="Only users with crud_career_path permission can delete global job families",
                        es="Solo usuarios con permiso crud_career_path pueden eliminar familias de trabajo globales",
                        slug="no-permission-for-global",
                    ),
                    code=403,
                )

        # If academy is set, ensure it matches the academy_id from URL
        elif academy_id and item.academy and item.academy.id != int(academy_id):
            raise ValidationException(
                translation(
                    lang,
                    en="Job family belongs to a different academy",
                    es="La familia de trabajo pertenece a otra academia",
                    slug="academy-mismatch",
                ),
                code=403,
            )

        # Check if there are related job roles
        if JobRole.objects.filter(job_family=item).exists():
            raise ValidationException(
                translation(
                    lang,
                    en="Cannot delete job family with associated job roles",
                    es="No se puede eliminar la familia de trabajo con roles asociados",
                    slug="has-job-roles",
                ),
                code=403,
            )

        item.delete()

        return Response(None, status=status.HTTP_204_NO_CONTENT)


class JobFamilyBySlugView(APIView):
    """
    Get, update, or delete a job family by slug.
    """

    @capable_of("read_career_path")
    def get(self, request, job_family_slug=None, academy_id=None):
        lang = get_user_language(request)

        item = JobFamily.objects.filter(slug=job_family_slug)
        item = apply_academy_filter(item, request, academy_id)

        item = item.first()

        if not item:
            raise ValidationException(
                translation(lang, en="Job family not found", es="Familia de trabajo no encontrada", slug="not-found"),
                code=404,
            )

        serializer = GetJobFamilySerializer(item, many=False)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @capable_of("crud_career_path")
    def put(self, request, job_family_slug=None, academy_id=None):
        lang = get_user_language(request)

        try:
            item = JobFamily.objects.get(slug=job_family_slug)
        except JobFamily.DoesNotExist:
            raise ValidationException(
                translation(lang, en="Job family not found", es="Familia de trabajo no encontrada", slug="not-found"),
                code=404,
            )

        # If academy is None, only allow users with crud_career_path permission
        if item.academy is None:
            if not validate_permission(request.user, "crud_career_path"):
                raise ValidationException(
                    translation(
                        lang,
                        en="Only users with crud_career_path permission can modify global job families",
                        es="Solo usuarios con permiso crud_career_path pueden modificar familias de trabajo globales",
                        slug="no-permission-for-global",
                    ),
                    code=403,
                )

        # If academy is set, ensure it matches the academy_id from URL
        elif academy_id and item.academy and item.academy.id != int(academy_id):
            raise ValidationException(
                translation(
                    lang,
                    en="Job family belongs to a different academy",
                    es="La familia de trabajo pertenece a otra academia",
                    slug="academy-mismatch",
                ),
                code=403,
            )

        serializer = JobFamilySerializer(item, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            # Return full data with GET serializer
            job_family = JobFamily.objects.get(id=item.id)
            response_serializer = GetJobFamilySerializer(job_family, many=False)
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of("crud_career_path")
    def delete(self, request, job_family_slug=None, academy_id=None):
        lang = get_user_language(request)

        try:
            item = JobFamily.objects.get(slug=job_family_slug)
        except JobFamily.DoesNotExist:
            raise ValidationException(
                translation(lang, en="Job family not found", es="Familia de trabajo no encontrada", slug="not-found"),
                code=404,
            )

        # If academy is None, only allow users with crud_career_path permission
        if item.academy is None:
            if not validate_permission(request.user, "crud_career_path"):
                raise ValidationException(
                    translation(
                        lang,
                        en="Only users with crud_career_path permission can delete global job families",
                        es="Solo usuarios con permiso crud_career_path pueden eliminar familias de trabajo globales",
                        slug="no-permission-for-global",
                    ),
                    code=403,
                )

        # If academy is set, ensure it matches the academy_id from URL
        elif academy_id and item.academy and item.academy.id != int(academy_id):
            raise ValidationException(
                translation(
                    lang,
                    en="Job family belongs to a different academy",
                    es="La familia de trabajo pertenece a otra academia",
                    slug="academy-mismatch",
                ),
                code=403,
            )

        # Check if there are related job roles
        if JobRole.objects.filter(job_family=item).exists():
            raise ValidationException(
                translation(
                    lang,
                    en="Cannot delete job family with associated job roles",
                    es="No se puede eliminar la familia de trabajo con roles asociados",
                    slug="has-job-roles",
                ),
                code=403,
            )

        item.delete()

        return Response(None, status=status.HTTP_204_NO_CONTENT)


class JobRoleView(APIView, GenerateLookupsMixin):
    """
    List all job roles or create a new job role.
    """

    extensions = APIViewExtensions(sort="name", paginate=True)

    @capable_of("read_career_path")
    def get(self, request, academy_id=None, job_family_id=None):
        handler = self.extensions(request)
        lang = get_user_language(request)

        items = JobRole.objects.filter()
        items = apply_academy_filter(items, request, academy_id)

        # Filter by job family if provided
        if job_family_id:
            items = items.filter(job_family__id=job_family_id)

        items = handler.queryset(items)
        serializer = GetJobRoleSerializer(items, many=True)

        return handler.response(serializer.data)

    @capable_of("crud_career_path")
    def post(self, request, academy_id=None):
        lang = get_user_language(request)

        data = {**request.data}

        # Set academy from URL parameter if provided
        if academy_id and "academy" not in data:
            data["academy"] = academy_id

        serializer = JobRoleSerializer(data=data, many=False)
        if serializer.is_valid():
            serializer.save()
            job_role = serializer.instance
            response_serializer = GetJobRoleSerializer(job_role, many=False)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class JobRoleByIdView(APIView):
    """
    Get, update, or delete a job role by id.
    """

    @capable_of("read_career_path")
    def get(self, request, job_role_id=None, academy_id=None):
        lang = get_user_language(request)

        item = JobRole.objects.filter(id=job_role_id)
        item = apply_academy_filter(item, request, academy_id)

        item = item.first()

        if not item:
            raise ValidationException(
                translation(lang, en="Job role not found", es="Rol de trabajo no encontrado", slug="not-found"),
                code=404,
            )

        serializer = GetJobRoleSerializer(item, many=False)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @capable_of("crud_career_path")
    def put(self, request, job_role_id=None, academy_id=None):
        lang = get_user_language(request)

        try:
            item = JobRole.objects.get(id=job_role_id)
        except JobRole.DoesNotExist:
            raise ValidationException(
                translation(lang, en="Job role not found", es="Rol de trabajo no encontrado", slug="not-found"),
                code=404,
            )

        # If academy is None, only allow users with crud_career_path permission
        if item.academy is None:
            if not validate_permission(request.user, "crud_career_path"):
                raise ValidationException(
                    translation(
                        lang,
                        en="Only users with crud_career_path permission can modify global job roles",
                        es="Solo usuarios con permiso crud_career_path pueden modificar roles de trabajo globales",
                        slug="no-permission-for-global",
                    ),
                    code=403,
                )

        # If academy is set, ensure it matches the academy_id from URL
        elif academy_id and item.academy and item.academy.id != int(academy_id):
            raise ValidationException(
                translation(
                    lang,
                    en="Job role belongs to a different academy",
                    es="El rol de trabajo pertenece a otra academia",
                    slug="academy-mismatch",
                ),
                code=403,
            )

        serializer = JobRoleSerializer(item, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            # Return full data with GET serializer
            job_role = JobRole.objects.get(id=item.id)
            response_serializer = GetJobRoleSerializer(job_role, many=False)
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of("crud_career_path")
    def delete(self, request, job_role_id=None, academy_id=None):
        lang = get_user_language(request)

        try:
            item = JobRole.objects.get(id=job_role_id)
        except JobRole.DoesNotExist:
            raise ValidationException(
                translation(lang, en="Job role not found", es="Rol de trabajo no encontrado", slug="not-found"),
                code=404,
            )

        # If academy is None, only allow users with crud_career_path permission
        if item.academy is None:
            if not validate_permission(request.user, "crud_career_path"):
                raise ValidationException(
                    translation(
                        lang,
                        en="Only users with crud_career_path permission can delete global job roles",
                        es="Solo usuarios con permiso crud_career_path pueden eliminar roles de trabajo globales",
                        slug="no-permission-for-global",
                    ),
                    code=403,
                )

        # If academy is set, ensure it matches the academy_id from URL
        elif academy_id and item.academy and item.academy.id != int(academy_id):
            raise ValidationException(
                translation(
                    lang,
                    en="Job role belongs to a different academy",
                    es="El rol de trabajo pertenece a otra academia",
                    slug="academy-mismatch",
                ),
                code=403,
            )

        # Check if there are related career paths
        from .models import CareerPath

        if CareerPath.objects.filter(job_role=item).exists():
            raise ValidationException(
                translation(
                    lang,
                    en="Cannot delete job role with associated career paths",
                    es="No se puede eliminar el rol de trabajo con trayectorias asociadas",
                    slug="has-career-paths",
                ),
                code=403,
            )

        item.delete()

        return Response(None, status=status.HTTP_204_NO_CONTENT)


class JobRoleBySlugView(APIView):
    """
    Get, update, or delete a job role by slug.
    """

    @capable_of("read_career_path")
    def get(self, request, job_role_slug=None, academy_id=None):
        lang = get_user_language(request)

        item = JobRole.objects.filter(slug=job_role_slug)
        item = apply_academy_filter(item, request, academy_id)

        item = item.first()

        if not item:
            raise ValidationException(
                translation(lang, en="Job role not found", es="Rol de trabajo no encontrado", slug="not-found"),
                code=404,
            )

        serializer = GetJobRoleSerializer(item, many=False)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @capable_of("crud_career_path")
    def put(self, request, job_role_slug=None, academy_id=None):
        lang = get_user_language(request)

        try:
            item = JobRole.objects.get(slug=job_role_slug)
        except JobRole.DoesNotExist:
            raise ValidationException(
                translation(lang, en="Job role not found", es="Rol de trabajo no encontrado", slug="not-found"),
                code=404,
            )

        # If academy is None, only allow users with crud_career_path permission
        if item.academy is None:
            if not validate_permission(request.user, "crud_career_path"):
                raise ValidationException(
                    translation(
                        lang,
                        en="Only users with crud_career_path permission can modify global job roles",
                        es="Solo usuarios con permiso crud_career_path pueden modificar roles de trabajo globales",
                        slug="no-permission-for-global",
                    ),
                    code=403,
                )

        # If academy is set, ensure it matches the academy_id from URL
        elif academy_id and item.academy and item.academy.id != int(academy_id):
            raise ValidationException(
                translation(
                    lang,
                    en="Job role belongs to a different academy",
                    es="El rol de trabajo pertenece a otra academia",
                    slug="academy-mismatch",
                ),
                code=403,
            )

        serializer = JobRoleSerializer(item, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            # Return full data with GET serializer
            job_role = JobRole.objects.get(id=item.id)
            response_serializer = GetJobRoleSerializer(job_role, many=False)
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of("crud_career_path")
    def delete(self, request, job_role_slug=None, academy_id=None):
        lang = get_user_language(request)

        try:
            item = JobRole.objects.get(slug=job_role_slug)
        except JobRole.DoesNotExist:
            raise ValidationException(
                translation(lang, en="Job role not found", es="Rol de trabajo no encontrado", slug="not-found"),
                code=404,
            )

        # If academy is None, only allow users with crud_career_path permission
        if item.academy is None:
            if not validate_permission(request.user, "crud_career_path"):
                raise ValidationException(
                    translation(
                        lang,
                        en="Only users with crud_career_path permission can delete global job roles",
                        es="Solo usuarios con permiso crud_career_path pueden eliminar roles de trabajo globales",
                        slug="no-permission-for-global",
                    ),
                    code=403,
                )

        # If academy is set, ensure it matches the academy_id from URL
        elif academy_id and item.academy and item.academy.id != int(academy_id):
            raise ValidationException(
                translation(
                    lang,
                    en="Job role belongs to a different academy",
                    es="El rol de trabajo pertenece a otra academia",
                    slug="academy-mismatch",
                ),
                code=403,
            )

        # Check if there are related career paths
        from .models import CareerPath

        if CareerPath.objects.filter(job_role=item).exists():
            raise ValidationException(
                translation(
                    lang,
                    en="Cannot delete job role with associated career paths",
                    es="No se puede eliminar el rol de trabajo con trayectorias asociadas",
                    slug="has-career-paths",
                ),
                code=403,
            )

        item.delete()

        return Response(None, status=status.HTTP_204_NO_CONTENT)



class SkillsView(APIView, GenerateLookupsMixin):
    """
    List all skills with optional filters by competency, job roles, technologies, and skill domains.
    """

    extensions = APIViewExtensions(sort="name", paginate=True)

    @capable_of("read_career_path")
    def get(self, request, academy_id=None):
        handler = self.extensions(request)
        lang = get_user_language(request)

        items = Skill.objects.all()

        # Filter by skill domains (comma-separated slugs)
        skill_domains = request.GET.get("skill_domains")
        if skill_domains:
            domain_slugs = [slug.strip() for slug in skill_domains.split(",") if slug.strip()]
            if domain_slugs:
                items = items.filter(domain__slug__in=domain_slugs)

        # Filter by technologies (comma-separated, matches if any technology is in the field)
        technologies = request.GET.get("technologies")
        if technologies:
            tech_list = [tech.strip() for tech in technologies.split(",") if tech.strip()]
            if tech_list:
                from django.db.models import Q

                tech_filter = Q()
                for tech in tech_list:
                    tech_filter |= Q(technologies__icontains=tech)
                items = items.filter(tech_filter)

        # Filter by competencies (comma-separated slugs)
        competencies = request.GET.get("competencies")
        if competencies:
            competency_slugs = [slug.strip() for slug in competencies.split(",") if slug.strip()]
            if competency_slugs:
                competency_skills = CompetencySkill.objects.filter(
                    competency__slug__in=competency_slugs
                )
                skill_ids = competency_skills.values_list("skill_id", flat=True).distinct()
                items = items.filter(id__in=skill_ids)

        # Filter by stages (comma-separated stage ids)
        stage_ids = request.GET.get("stage_ids")
        if stage_ids:
            parsed_stage_ids = []
            for raw in [x.strip() for x in stage_ids.split(",") if x.strip()]:
                if raw.isdigit():
                    parsed_stage_ids.append(int(raw))
            if parsed_stage_ids:
                stage_skill_ids = (
                    StageSkill.objects.filter(stage_id__in=parsed_stage_ids)
                    .values_list("skill_id", flat=True)
                    .distinct()
                )
                items = items.filter(id__in=stage_skill_ids)

        # Filter by career paths (ids and/or names)
        career_path_ids_param = request.GET.get("career_path_ids")
        career_paths_param = request.GET.get("career_paths")
        if career_path_ids_param or career_paths_param:
            candidate_values = []
            if career_path_ids_param:
                candidate_values.extend([x.strip() for x in career_path_ids_param.split(",") if x.strip()])
            if career_paths_param:
                candidate_values.extend([x.strip() for x in career_paths_param.split(",") if x.strip()])

            parsed_ids = []
            parsed_names = []
            for raw in candidate_values:
                if raw.isdigit():
                    parsed_ids.append(int(raw))
                else:
                    parsed_names.append(raw)

            path_qs = CareerPath.objects.all()
            if parsed_ids:
                path_qs = path_qs.filter(id__in=parsed_ids)
            if parsed_names:
                path_qs = path_qs.filter(name__in=parsed_names)

            career_path_ids = list(path_qs.values_list("id", flat=True).distinct())
            if career_path_ids:
                stage_ids_for_paths = CareerStage.objects.filter(career_path_id__in=career_path_ids).values_list(
                    "id", flat=True
                )
                path_skill_ids = (
                    StageSkill.objects.filter(stage_id__in=stage_ids_for_paths)
                    .values_list("skill_id", flat=True)
                    .distinct()
                )
                items = items.filter(id__in=path_skill_ids)

        # Filter by job roles (comma-separated slugs)
        job_roles = request.GET.get("job_roles")
        if job_roles:
            role_slugs = [slug.strip() for slug in job_roles.split(",") if slug.strip()]
            if role_slugs:
                # Get competencies through: JobRole -> CareerPath -> CareerStage -> StageCompetency -> Competency
                # Then get skills through: Competency -> CompetencySkill -> Skill
                stage_competencies = StageCompetency.objects.filter(
                    stage__career_path__job_role__slug__in=role_slugs
                )
                competency_ids = stage_competencies.values_list("competency_id", flat=True).distinct()
                competency_skills = CompetencySkill.objects.filter(competency_id__in=competency_ids)
                skill_ids = competency_skills.values_list("skill_id", flat=True).distinct()
                items = items.filter(id__in=skill_ids)

        items = handler.queryset(items)
        serializer = SkillSerializer(items, many=True)

        return handler.response(serializer.data)


class CompetenciesView(APIView, GenerateLookupsMixin):
    """
    List all competencies with optional filters by job roles and technologies.
    Includes an array of skill slugs and names.
    """

    extensions = APIViewExtensions(sort="name", paginate=True)

    @capable_of("read_career_path")
    def get(self, request, academy_id=None):
        handler = self.extensions(request)
        lang = get_user_language(request)

        items = Competency.objects.all()

        # Filter by technologies (comma-separated, matches if any technology is in the field)
        technologies = request.GET.get("technologies")
        if technologies:
            tech_list = [tech.strip() for tech in technologies.split(",") if tech.strip()]
            if tech_list:
                from django.db.models import Q

                tech_filter = Q()
                for tech in tech_list:
                    tech_filter |= Q(technologies__icontains=tech)
                items = items.filter(tech_filter)

        # Filter by job roles (comma-separated slugs)
        job_roles = request.GET.get("job_roles")
        if job_roles:
            role_slugs = [slug.strip() for slug in job_roles.split(",") if slug.strip()]
            if role_slugs:
                # Get competencies through: JobRole -> CareerPath -> CareerStage -> StageCompetency -> Competency
                stage_competencies = StageCompetency.objects.filter(
                    stage__career_path__job_role__slug__in=role_slugs
                )
                competency_ids = stage_competencies.values_list("competency_id", flat=True).distinct()
                items = items.filter(id__in=competency_ids)

        items = handler.queryset(items)
        serializer = CompetencySerializer(items, many=True)

        return handler.response(serializer.data)


class JobRolesByFamilyView(APIView, GenerateLookupsMixin):
    """
    List all job roles from a specific job family.
    Includes an array of career paths (id and name) for each job role.
    """

    extensions = APIViewExtensions(sort="name", paginate=True)

    @capable_of("read_career_path")
    def get(self, request, job_family_id=None, academy_id=None):
        handler = self.extensions(request)
        lang = get_user_language(request)

        items = JobRole.objects.filter()

        # Filter by job family (required)
        if job_family_id:
            items = items.filter(job_family__id=job_family_id)
        else:
            raise ValidationException(
                translation(lang, en="Job family ID is required", es="El ID de la familia de trabajo es requerido", slug="job_family_required"),
                code=400,
            )

        items = apply_academy_filter(items, request, academy_id)

        items = handler.queryset(items)
        serializer = JobRoleWithCareerPathsSerializer(items, many=True)

        return handler.response(serializer.data)


class CareerPathsView(APIView, GenerateLookupsMixin):
    """
    List all career paths with their stages included.
    """

    extensions = APIViewExtensions(sort="name", paginate=True)

    @capable_of("read_career_path")
    def get(self, request, academy_id=None):
        handler = self.extensions(request)
        lang = get_user_language(request)

        items = CareerPath.objects.filter()
        items = apply_academy_filter(items, request, academy_id)

        # Filter by job roles (supports ids and slugs, comma-separated)
        job_role_ids = request.GET.get("job_role_ids")
        job_roles = request.GET.get("job_roles")
        if job_role_ids or job_roles:
            parsed_role_ids = []
            if job_role_ids:
                for raw in [x.strip() for x in job_role_ids.split(",") if x.strip()]:
                    if raw.isdigit():
                        parsed_role_ids.append(int(raw))

            role_slugs = []
            if job_roles:
                role_slugs = [x.strip() for x in job_roles.split(",") if x.strip()]

            if parsed_role_ids:
                items = items.filter(job_role_id__in=parsed_role_ids)
            if role_slugs:
                items = items.filter(job_role__slug__in=role_slugs)

        items = handler.queryset(items)
        serializer = CareerPathWithStagesSerializer(items, many=True)

        return handler.response(serializer.data)

    @capable_of("crud_career_path")
    def post(self, request, academy_id=None):
        lang = get_user_language(request)

        data = {**request.data}
        if academy_id and "academy" not in data:
            data["academy"] = academy_id

        serializer = CareerPathSerializer(data=data, many=False)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            job_role = JobRole.objects.get(id=serializer.validated_data["job_role"])
        except JobRole.DoesNotExist:
            raise ValidationException(
                translation(lang, en="Job role not found", es="Rol de trabajo no encontrado", slug="not-found"),
                code=404,
            )
        assert_job_role_visible_for_academy(request, lang, job_role, academy_id)

        serializer.save()
        career_path = serializer.instance
        response_serializer = CareerPathWithStagesSerializer(career_path, many=False)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class CareerPathByIdView(APIView):
    """
    Delete a career path by id (blocked while stages exist).
    """

    @capable_of("crud_career_path")
    def delete(self, request, career_path_id=None, academy_id=None):
        lang = get_user_language(request)

        item = get_career_path_or_404(lang, career_path_id)
        assert_mutable_career_path(request, lang, item, academy_id)

        if CareerStage.objects.filter(career_path=item).exists():
            raise ValidationException(
                translation(
                    lang,
                    en="Cannot delete career path with associated stages",
                    es="No se puede eliminar la trayectoria con etapas asociadas",
                    slug="has-career-stages",
                ),
                code=403,
            )

        item.delete()
        return Response(None, status=status.HTTP_204_NO_CONTENT)


class CareerStagesByPathView(APIView):
    """
    Create a career stage under a career path.
    """

    @capable_of("crud_career_path")
    def post(self, request, career_path_id=None, academy_id=None):
        lang = get_user_language(request)

        path = get_career_path_or_404(lang, career_path_id)
        assert_mutable_career_path(request, lang, path, academy_id)

        serializer = CareerStageCreateSerializer(
            data=request.data,
            many=False,
            context={"career_path": path},
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            stage = serializer.save()
        except IntegrityError:
            raise ValidationException(
                translation(
                    lang,
                    en="A stage with this sequence already exists for this career path",
                    es="Ya existe una etapa con esta secuencia en esta trayectoria",
                    slug="career-stage-sequence-conflict",
                ),
                code=400,
            )

        return Response(CareerStageSmallSerializer(stage, many=False).data, status=status.HTTP_201_CREATED)


class CareerStagesView(APIView, GenerateLookupsMixin):
    """
    List career stages with optional filters by career path and job role.
    """

    extensions = APIViewExtensions(sort="sequence", paginate=True)

    @capable_of("read_career_path")
    def get(self, request, academy_id=None):
        handler = self.extensions(request)

        items = CareerStage.objects.select_related("career_path", "career_path__job_role").filter()
        items = apply_academy_filter(items, request, academy_id, academy_field="career_path__academy")

        # Filter by career paths (ids, comma-separated)
        career_path_ids = request.GET.get("career_path_ids")
        if career_path_ids:
            parsed_path_ids = []
            for raw in [x.strip() for x in career_path_ids.split(",") if x.strip()]:
                if raw.isdigit():
                    parsed_path_ids.append(int(raw))
            if parsed_path_ids:
                items = items.filter(career_path_id__in=parsed_path_ids)

        # Filter by job roles (supports ids and slugs, comma-separated)
        job_role_ids = request.GET.get("job_role_ids")
        job_roles = request.GET.get("job_roles")
        if job_role_ids:
            parsed_role_ids = []
            for raw in [x.strip() for x in job_role_ids.split(",") if x.strip()]:
                if raw.isdigit():
                    parsed_role_ids.append(int(raw))
            if parsed_role_ids:
                items = items.filter(career_path__job_role_id__in=parsed_role_ids)

        if job_roles:
            role_slugs = [x.strip() for x in job_roles.split(",") if x.strip()]
            if role_slugs:
                items = items.filter(career_path__job_role__slug__in=role_slugs)

        items = handler.queryset(items)
        serializer = CareerStageListSerializer(items, many=True)
        return handler.response(serializer.data)


class CareerStageByPathView(APIView):
    """
    Delete a career stage under a career path (blocked if stage skills or stage competencies exist).
    """

    @capable_of("crud_career_path")
    def delete(self, request, career_path_id=None, career_stage_id=None, academy_id=None):
        lang = get_user_language(request)

        path = get_career_path_or_404(lang, career_path_id)
        assert_mutable_career_path(request, lang, path, academy_id)

        try:
            stage = CareerStage.objects.get(id=career_stage_id, career_path_id=path.id)
        except CareerStage.DoesNotExist:
            raise ValidationException(
                translation(lang, en="Career stage not found", es="Etapa no encontrada", slug="not-found"),
                code=404,
            )

        if StageSkill.objects.filter(stage=stage).exists() or StageCompetency.objects.filter(stage=stage).exists():
            raise ValidationException(
                translation(
                    lang,
                    en="Cannot delete career stage with associated stage skills or competencies",
                    es="No se puede eliminar la etapa con habilidades o competencias asociadas",
                    slug="has-stage-links",
                ),
                code=403,
            )

        stage.delete()
        return Response(None, status=status.HTTP_204_NO_CONTENT)


class StageSkillCreateView(APIView):
    """
    Create a global Skill (if missing) and anchor it to a CareerStage via StageSkill.
    """

    @capable_of("crud_career_path")
    def post(self, request, academy_id=None):
        lang = get_user_language(request)

        serializer = StageSkillCreateSerializer(data=request.data, many=False)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data

        stage = (
            CareerStage.objects.filter(id=data["stage_id"])
            .select_related("career_path", "career_path__academy")
            .first()
        )
        if not stage:
            raise ValidationException(
                translation(lang, en="Career stage not found", es="Etapa no encontrada", slug="not-found"),
                code=404,
            )

        assert_mutable_career_path(request, lang, stage.career_path, academy_id)

        if data.get("domain_id") is not None:
            domain = SkillDomain.objects.filter(id=data["domain_id"]).first()
        else:
            domain = SkillDomain.objects.filter(slug=data["domain_slug"]).first()

        if not domain:
            raise ValidationException(
                translation(
                    lang,
                    en="Skill domain not found",
                    es="Dominio de habilidad no encontrado",
                    slug="skill-domain-not-found",
                ),
                code=404,
            )

        name = data["name"]
        skill_slug = (data.get("slug") or "").strip() or slugify(name)

        existing_skill = Skill.objects.filter(slug=skill_slug).first()
        if existing_skill:
            if existing_skill.domain_id != domain.id:
                raise ValidationException(
                    translation(
                        lang,
                        en="A skill with this slug already exists under a different domain",
                        es="Ya existe una habilidad con este slug en otro dominio",
                        slug="skill-slug-domain-mismatch",
                    ),
                    code=400,
                )
            skill = existing_skill
        else:
            skill = Skill.objects.create(
                slug=skill_slug,
                name=name,
                domain=domain,
                description=data.get("description") or "",
                technologies=data.get("technologies") or "",
            )

        stage_skill, ss_created = StageSkill.objects.update_or_create(
            stage=stage,
            skill=skill,
            defaults={
                "required_level": data["required_level"],
                "is_core": data["is_core"],
            },
        )

        response_status = status.HTTP_201_CREATED if ss_created else status.HTTP_200_OK
        return Response(
            {
                "skill": SkillSerializer(skill, many=False).data,
                "stage_skill": StageAssignmentSerializer(stage_skill, many=False).data,
            },
            status=response_status,
        )


class SkillDomainsView(APIView, GenerateLookupsMixin):
    """
    List all skill domains.
    """

    extensions = APIViewExtensions(sort="name", paginate=True)

    @capable_of("read_career_path")
    def get(self, request, academy_id=None):
        handler = self.extensions(request)
        lang = get_user_language(request)

        items = SkillDomain.objects.all()

        items = handler.queryset(items)
        serializer = SkillDomainSerializer(items, many=True)

        return handler.response(serializer.data)

    @capable_of("crud_career_path")
    def post(self, request, academy_id=None):
        lang = get_user_language(request)

        serializer = SkillDomainWriteSerializer(data=request.data, many=False)
        if serializer.is_valid():
            serializer.save()
            domain = serializer.instance
            response_serializer = SkillDomainSerializer(domain, many=False)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SkillDomainByIdView(APIView):
    """
    Delete a skill domain by id (blocked while skills reference it).
    """

    @capable_of("crud_career_path")
    def delete(self, request, skill_domain_id=None, academy_id=None):
        lang = get_user_language(request)

        try:
            item = SkillDomain.objects.get(id=skill_domain_id)
        except SkillDomain.DoesNotExist:
            raise ValidationException(
                translation(
                    lang,
                    en="Skill domain not found",
                    es="Dominio de habilidad no encontrado",
                    slug="not-found",
                ),
                code=404,
            )

        if Skill.objects.filter(domain=item).exists():
            raise ValidationException(
                translation(
                    lang,
                    en="Cannot delete skill domain with associated skills",
                    es="No se puede eliminar el dominio con habilidades asociadas",
                    slug="has-skills",
                ),
                code=403,
            )

        item.delete()
        return Response(None, status=status.HTTP_204_NO_CONTENT)


class SkillDomainBySlugView(APIView):
    """
    Delete a skill domain by slug (blocked while skills reference it).
    """

    @capable_of("crud_career_path")
    def delete(self, request, skill_domain_slug=None, academy_id=None):
        lang = get_user_language(request)

        try:
            item = SkillDomain.objects.get(slug=skill_domain_slug)
        except SkillDomain.DoesNotExist:
            raise ValidationException(
                translation(
                    lang,
                    en="Skill domain not found",
                    es="Dominio de habilidad no encontrado",
                    slug="not-found",
                ),
                code=404,
            )

        if Skill.objects.filter(domain=item).exists():
            raise ValidationException(
                translation(
                    lang,
                    en="Cannot delete skill domain with associated skills",
                    es="No se puede eliminar el dominio con habilidades asociadas",
                    slug="has-skills",
                ),
                code=403,
            )

        item.delete()
        return Response(None, status=status.HTTP_204_NO_CONTENT)


class SkillKnowledgeItemsView(APIView, GenerateLookupsMixin):
    """
    List all skill knowledge items with optional filter by skill (via query string).
    """

    extensions = APIViewExtensions(sort="id", paginate=True)

    @capable_of("read_career_path")
    def get(self, request, academy_id=None):
        handler = self.extensions(request)
        lang = get_user_language(request)

        items = SkillKnowledgeItem.objects.all()

        # Filter by skill (comma-separated slugs)
        skill_slugs = request.GET.get("skill")
        if skill_slugs:
            skill_list = [slug.strip() for slug in skill_slugs.split(",") if slug.strip()]
            if skill_list:
                items = items.filter(skill__slug__in=skill_list)

        items = handler.queryset(items)
        serializer = SkillKnowledgeItemSerializer(items, many=True)

        return handler.response(serializer.data)


class SkillAttitudeTagsView(APIView, GenerateLookupsMixin):
    """
    List all attitude tags with optional filter by skill (via query string).
    """

    extensions = APIViewExtensions(sort="tag", paginate=True)

    @capable_of("read_career_path")
    def get(self, request, academy_id=None):
        handler = self.extensions(request)
        lang = get_user_language(request)

        items = SkillAttitudeTag.objects.all()

        # Filter by skill (comma-separated slugs)
        skill_slugs = request.GET.get("skill")
        if skill_slugs:
            skill_list = [slug.strip() for slug in skill_slugs.split(",") if slug.strip()]
            if skill_list:
                items = items.filter(skill__slug__in=skill_list)

        items = handler.queryset(items)
        serializer = SkillAttitudeTagSerializer(items, many=True)

        return handler.response(serializer.data)


class SkillByIdView(APIView):
    """
    Get a single skill by id with all nested information.
    """

    @capable_of("read_career_path")
    def get(self, request, skill_id=None, academy_id=None):
        lang = get_user_language(request)

        try:
            item = Skill.objects.get(id=skill_id)
        except Skill.DoesNotExist:
            raise ValidationException(
                translation(lang, en="Skill not found", es="Habilidad no encontrada", slug="not-found"),
                code=404,
            )

        serializer = SkillDetailSerializer(item, many=False)
        return Response(serializer.data, status=status.HTTP_200_OK)


class SkillBySlugView(APIView):
    """
    Get a single skill by slug with all nested information.
    """

    @capable_of("read_career_path")
    def get(self, request, skill_slug=None, academy_id=None):
        lang = get_user_language(request)

        try:
            item = Skill.objects.get(slug=skill_slug)
        except Skill.DoesNotExist:
            raise ValidationException(
                translation(lang, en="Skill not found", es="Habilidad no encontrada", slug="not-found"),
                code=404,
            )

        serializer = SkillDetailSerializer(item, many=False)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CompetencyByIdView(APIView):
    """
    Get a single competency by id with all nested information.
    """

    @capable_of("read_career_path")
    def get(self, request, competency_id=None, academy_id=None):
        lang = get_user_language(request)

        try:
            item = Competency.objects.get(id=competency_id)
        except Competency.DoesNotExist:
            raise ValidationException(
                translation(lang, en="Competency not found", es="Competencia no encontrada", slug="not-found"),
                code=404,
            )

        serializer = CompetencyDetailSerializer(item, many=False)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CompetencyBySlugView(APIView):
    """
    Get a single competency by slug with all nested information.
    """

    @capable_of("read_career_path")
    def get(self, request, competency_slug=None, academy_id=None):
        lang = get_user_language(request)

        try:
            item = Competency.objects.get(slug=competency_slug)
        except Competency.DoesNotExist:
            raise ValidationException(
                translation(lang, en="Competency not found", es="Competencia no encontrada", slug="not-found"),
                code=404,
            )

        serializer = CompetencyDetailSerializer(item, many=False)
        return Response(serializer.data, status=status.HTTP_200_OK)
