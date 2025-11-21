from slugify import slugify
from rest_framework import serializers
from capyc.core.i18n import translation
from capyc.rest_framework.exceptions import ValidationException

from breathecode.utils import serpy

from .models import (
    CareerPath,
    CareerStage,
    Competency,
    JobFamily,
    JobRole,
    Skill,
    SkillAttitudeTag,
    SkillDomain,
    SkillKnowledgeItem,
)


# GET Serializers (using Serpy)
class GetAcademySerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()


class GetJobFamilySerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()
    description = serpy.Field()
    academy = GetAcademySerializer(required=False)
    is_active = serpy.Field()
    created_at = serpy.Field()
    updated_at = serpy.Field()


class GetJobFamilySerializerSmall(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()


class GetJobRoleSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()
    job_family = GetJobFamilySerializerSmall(required=False)
    description = serpy.Field()
    academy = GetAcademySerializer(required=False)
    is_active = serpy.Field()
    is_model = serpy.Field()
    created_at = serpy.Field()
    updated_at = serpy.Field()


# POST/PUT Serializers (using DRF)
class JobFamilySerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    slug = serializers.SlugField(required=False)
    academy = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = JobFamily
        fields = (
            "id",
            "slug",
            "name",
            "description",
            "academy",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_at", "updated_at")

    def validate(self, attrs):
        slug = attrs.get("slug")
        if not self.instance and not slug and attrs.get("name"):
            slug = slugify(attrs["name"])
            attrs["slug"] = slug
        if slug:
            queryset = JobFamily.objects.all()
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.filter(slug=slug).exists():
                raise ValidationException(
                    translation(
                        en=f"A job family with slug '{slug}' already exists",
                        es=f"Ya existe una familia laboral con el slug '{slug}'",
                        slug="job-family-slug-exists",
                    ),
                    code=400,
                )
        return super().validate(attrs)

    def create(self, validated_data):
        # Handle academy ID conversion
        if "academy" in validated_data and isinstance(validated_data["academy"], int):
            from breathecode.admissions.models import Academy

            academy_id = validated_data.pop("academy")
            if academy_id:
                validated_data["academy"] = Academy.objects.get(id=academy_id)
            else:
                validated_data["academy"] = None

        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Handle academy ID conversion
        if "academy" in validated_data and isinstance(validated_data["academy"], int):
            from breathecode.admissions.models import Academy

            academy_id = validated_data.pop("academy")
            if academy_id:
                validated_data["academy"] = Academy.objects.get(id=academy_id)
            else:
                validated_data["academy"] = None

        return super().update(instance, validated_data)


class JobRoleSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    slug = serializers.SlugField(required=False)
    job_family = serializers.IntegerField()
    academy = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = JobRole
        fields = (
            "id",
            "slug",
            "name",
            "job_family",
            "description",
            "academy",
            "is_active",
            "is_model",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_at", "updated_at")

    def validate(self, attrs):
        slug = attrs.get("slug")
        if not self.instance and not slug and attrs.get("name"):
            slug = slugify(attrs["name"])
            attrs["slug"] = slug
        if slug:
            queryset = JobRole.objects.all()
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.filter(slug=slug).exists():
                raise ValidationException(
                    translation(
                        en=f"A job role with slug '{slug}' already exists",
                        es=f"Ya existe un rol laboral con el slug '{slug}'",
                        slug="job-role-slug-exists",
                    ),
                    code=400,
                )

        return super().validate(attrs)

    def create(self, validated_data):
        # Handle job_family ID conversion
        if "job_family" in validated_data and isinstance(validated_data["job_family"], int):
            job_family_id = validated_data.pop("job_family")
            validated_data["job_family"] = JobFamily.objects.get(id=job_family_id)

        # Handle academy ID conversion
        if "academy" in validated_data and isinstance(validated_data["academy"], int):
            from breathecode.admissions.models import Academy

            academy_id = validated_data.pop("academy")
            if academy_id:
                validated_data["academy"] = Academy.objects.get(id=academy_id)
            else:
                validated_data["academy"] = None

        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Handle job_family ID conversion
        if "job_family" in validated_data and isinstance(validated_data["job_family"], int):
            job_family_id = validated_data.pop("job_family")
            validated_data["job_family"] = JobFamily.objects.get(id=job_family_id)

        # Handle academy ID conversion
        if "academy" in validated_data and isinstance(validated_data["academy"], int):
            from breathecode.admissions.models import Academy

            academy_id = validated_data.pop("academy")
            if academy_id:
                validated_data["academy"] = Academy.objects.get(id=academy_id)
            else:
                validated_data["academy"] = None

        return super().update(instance, validated_data)


# Additional GET Serializers for new endpoints
class SkillDomainSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()


class SkillSmallSerializer(serpy.Serializer):
    slug = serpy.Field()
    name = serpy.Field()


class CompetencySmallSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()


class CareerPathSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    name = serpy.Field()


class CareerStageSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    sequence = serpy.Field()
    title = serpy.Field()
    goal = serpy.Field()
    description = serpy.Field()


class SkillSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()
    domain = SkillDomainSmallSerializer(required=False)
    description = serpy.Field()
    technologies = serpy.Field()
    created_at = serpy.Field()
    updated_at = serpy.Field()


class CompetencySerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()
    type = serpy.Field()
    description = serpy.Field()
    technologies = serpy.Field()
    skills = serpy.MethodField()
    created_at = serpy.Field()
    updated_at = serpy.Field()

    def get_skills(self, obj):
        from .models import CompetencySkill

        competency_skills = CompetencySkill.objects.filter(competency=obj)
        skills = [cs.skill for cs in competency_skills]
        return SkillSmallSerializer(skills, many=True).data


class JobRoleWithCareerPathsSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()
    job_family = GetJobFamilySerializerSmall(required=False)
    description = serpy.Field()
    academy = GetAcademySerializer(required=False)
    is_active = serpy.Field()
    is_model = serpy.Field()
    career_paths = serpy.MethodField()
    created_at = serpy.Field()
    updated_at = serpy.Field()

    def get_career_paths(self, obj):
        career_paths = CareerPath.objects.filter(job_role=obj)
        return CareerPathSmallSerializer(career_paths, many=True).data


class CareerPathWithStagesSerializer(serpy.Serializer):
    id = serpy.Field()
    name = serpy.Field()
    job_role = GetJobRoleSerializer(required=False)
    description = serpy.Field()
    academy = GetAcademySerializer(required=False)
    is_active = serpy.Field()
    stages = serpy.MethodField()
    created_at = serpy.Field()
    updated_at = serpy.Field()

    def get_stages(self, obj):
        stages = CareerStage.objects.filter(career_path=obj).order_by("sequence")
        return CareerStageSmallSerializer(stages, many=True).data


class SkillDomainSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()
    description = serpy.Field()
    created_at = serpy.Field()
    updated_at = serpy.Field()


class SkillKnowledgeItemSerializer(serpy.Serializer):
    id = serpy.Field()
    skill = SkillSmallSerializer(required=False)
    description = serpy.Field()
    created_at = serpy.Field()
    updated_at = serpy.Field()


class SkillAttitudeTagSerializer(serpy.Serializer):
    id = serpy.Field()
    skill = SkillSmallSerializer(required=False)
    tag = serpy.Field()
    description = serpy.Field()
    created_at = serpy.Field()
    updated_at = serpy.Field()


# Helper serializers for detailed views
class SkillBehaviorIndicatorSerializer(serpy.Serializer):
    id = serpy.Field()
    level = serpy.Field()
    description = serpy.Field()
    created_at = serpy.Field()
    updated_at = serpy.Field()


class SkillKnowledgeItemWithoutSkillSerializer(serpy.Serializer):
    id = serpy.Field()
    description = serpy.Field()
    created_at = serpy.Field()
    updated_at = serpy.Field()


class SkillAttitudeTagWithoutSkillSerializer(serpy.Serializer):
    id = serpy.Field()
    tag = serpy.Field()
    description = serpy.Field()
    created_at = serpy.Field()
    updated_at = serpy.Field()


class CompetencyWithWeightSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()
    type = serpy.Field()
    weight = serpy.Field(required=False)


class StageAssignmentSerializer(serpy.Serializer):
    id = serpy.Field()
    stage = serpy.MethodField()
    required_level = serpy.Field()
    is_core = serpy.Field()
    created_at = serpy.Field()
    updated_at = serpy.Field()

    def get_stage(self, obj):
        return {
            "id": obj.stage.id,
            "title": obj.stage.title,
            "sequence": obj.stage.sequence,
            "career_path": {
                "id": obj.stage.career_path.id,
                "name": obj.stage.career_path.name,
                "job_role": {
                    "id": obj.stage.career_path.job_role.id,
                    "slug": obj.stage.career_path.job_role.slug,
                    "name": obj.stage.career_path.job_role.name,
                },
            },
        }


# Detailed serializers for single resource endpoints
class SkillDetailSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()
    domain = SkillDomainSmallSerializer(required=False)
    description = serpy.Field()
    technologies = serpy.Field()    
    knowledge_items = serpy.MethodField()
    attitude_tags = serpy.MethodField()
    behavioral_indicators = serpy.MethodField()
    competencies = serpy.MethodField()
    created_at = serpy.Field()
    updated_at = serpy.Field()

    def get_knowledge_items(self, obj):
        knowledge_items = obj.knowledge_items.all()
        return SkillKnowledgeItemWithoutSkillSerializer(knowledge_items, many=True).data

    def get_attitude_tags(self, obj):
        attitude_tags = obj.attitude_tags.all()
        return SkillAttitudeTagWithoutSkillSerializer(attitude_tags, many=True).data

    def get_behavioral_indicators(self, obj):
        behavioral_indicators = obj.behavioral_indicators.all()
        return SkillBehaviorIndicatorSerializer(behavioral_indicators, many=True).data

    def get_competencies(self, obj):
        from .models import CompetencySkill

        competency_skills = CompetencySkill.objects.filter(skill=obj).select_related("competency")
        return [
            {
                "id": cs.competency.id,
                "slug": cs.competency.slug,
                "name": cs.competency.name,
                "type": cs.competency.type,
                "weight": float(cs.weight) if cs.weight else None,
            }
            for cs in competency_skills
        ]


class CompetencyDetailSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()
    type = serpy.Field()
    description = serpy.Field()
    technologies = serpy.Field()
    skills = serpy.MethodField()
    stage_assignments = serpy.MethodField()
    created_at = serpy.Field()
    updated_at = serpy.Field()

    def get_skills(self, obj):
        from .models import CompetencySkill

        competency_skills = CompetencySkill.objects.filter(competency=obj).select_related("skill")
        return [
            {
                "id": cs.skill.id,
                "slug": cs.skill.slug,
                "name": cs.skill.name,
                "domain": {
                    "id": cs.skill.domain.id,
                    "slug": cs.skill.domain.slug,
                    "name": cs.skill.domain.name,
                }
                if cs.skill.domain
                else None,
                "weight": float(cs.weight) if cs.weight else None,
            }
            for cs in competency_skills
        ]

    def get_stage_assignments(self, obj):
        from .models import StageCompetency

        stage_assignments = (
            StageCompetency.objects.filter(competency=obj)
            .select_related("stage", "stage__career_path", "stage__career_path__job_role")
            .order_by("stage__career_path__job_role__name", "stage__sequence")
        )
        return StageAssignmentSerializer(stage_assignments, many=True).data
