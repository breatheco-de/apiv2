from capyc.core.i18n import translation
from capyc.rest_framework.exceptions import ValidationException
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from breathecode.authenticate.actions import get_user_language
from breathecode.utils import GenerateLookupsMixin, capable_of
from breathecode.utils.api_view_extensions.api_view_extensions import APIViewExtensions
from breathecode.utils.decorators.has_permission import validate_permission

from .models import (
    CareerPath,
    Competency,
    CompetencySkill,
    JobFamily,
    JobRole,
    Skill,
    SkillAttitudeTag,
    SkillDomain,
    SkillKnowledgeItem,
    StageCompetency,
)
from .serializers import (
    CareerPathWithStagesSerializer,
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
    SkillKnowledgeItemSerializer,
    SkillSerializer,
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
            # Return full data with GET serializer
            job_family = JobFamily.objects.get(id=serializer.data["id"])
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
        elif academy_id and item.academy and item.academy.id != academy_id:
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
        elif academy_id and item.academy and item.academy.id != academy_id:
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
        elif academy_id and item.academy and item.academy.id != academy_id:
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
        elif academy_id and item.academy and item.academy.id != academy_id:
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
            # Return full data with GET serializer
            job_role = JobRole.objects.get(id=serializer.data["id"])
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
        elif academy_id and item.academy and item.academy.id != academy_id:
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
        elif academy_id and item.academy and item.academy.id != academy_id:
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
        elif academy_id and item.academy and item.academy.id != academy_id:
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
        elif academy_id and item.academy and item.academy.id != academy_id:
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

        items = handler.queryset(items)
        serializer = CareerPathWithStagesSerializer(items, many=True)

        return handler.response(serializer.data)


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
