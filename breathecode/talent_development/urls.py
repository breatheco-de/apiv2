from django.urls import path

from .views import (
    CareerPathByIdView,
    CareerPathsView,
    CareerStageByPathView,
    CareerStagesByPathView,
    CompetenciesView,
    CompetencyByIdView,
    CompetencyBySlugView,
    JobFamilyByIdView,
    JobFamilyBySlugView,
    JobFamilyView,
    JobRoleByIdView,
    JobRoleBySlugView,
    JobRolesByFamilyView,
    JobRoleView,
    SkillAttitudeTagsView,
    SkillByIdView,
    SkillBySlugView,
    SkillDomainByIdView,
    SkillDomainBySlugView,
    SkillDomainsView,
    SkillKnowledgeItemsView,
    SkillsView,
    StageSkillCreateView,
)

app_name = "talent_development"
urlpatterns = [
    # Academy-scoped endpoints
    # Job Family endpoints
    path("academy/job_family", JobFamilyView.as_view(), name="academy_job_family"),
    path("academy/job_family/<int:job_family_id>", JobFamilyByIdView.as_view(), name="academy_job_family_id"),
    path("academy/job_family/<str:job_family_slug>", JobFamilyBySlugView.as_view(), name="academy_job_family_slug"),
    # Job Role endpoints
    path("academy/job_role", JobRoleView.as_view(), name="academy_job_role"),
    path("academy/job_role/<int:job_role_id>", JobRoleByIdView.as_view(), name="academy_job_role_id"),
    path("academy/job_role/<str:job_role_slug>", JobRoleBySlugView.as_view(), name="academy_job_role_slug"),
    path("academy/job_family/<int:job_family_id>/job_role", JobRolesByFamilyView.as_view(), name="academy_job_family_id_role"),
    # Skill and Competency endpoints
    path("academy/skill", SkillsView.as_view(), name="academy_skill"),
    path("academy/skill/<int:skill_id>", SkillByIdView.as_view(), name="academy_skill_id"),
    path("academy/skill/<str:skill_slug>", SkillBySlugView.as_view(), name="academy_skill_slug"),
    path("academy/stage_skill", StageSkillCreateView.as_view(), name="academy_stage_skill"),
    path("academy/competency", CompetenciesView.as_view(), name="academy_competency"),
    path("academy/competency/<int:competency_id>", CompetencyByIdView.as_view(), name="academy_competency_id"),
    path("academy/competency/<str:competency_slug>", CompetencyBySlugView.as_view(), name="academy_competency_slug"),
    path("academy/skill_domain/<int:skill_domain_id>", SkillDomainByIdView.as_view(), name="academy_skill_domain_id"),
    path("academy/skill_domain/<str:skill_domain_slug>", SkillDomainBySlugView.as_view(), name="academy_skill_domain_slug"),
    path("academy/skill_domain", SkillDomainsView.as_view(), name="academy_skill_domain"),
    path("academy/skill_knowledge_item", SkillKnowledgeItemsView.as_view(), name="academy_skill_knowledge_item"),
    path("academy/skill_attitude_tag", SkillAttitudeTagsView.as_view(), name="academy_skill_attitude_tag"),
    # Career Path endpoints (nested career_stage routes before career_path/<id>)
    path(
        "academy/career_path/<int:career_path_id>/career_stage/<int:career_stage_id>",
        CareerStageByPathView.as_view(),
        name="academy_career_path_id_career_stage_id",
    ),
    path(
        "academy/career_path/<int:career_path_id>/career_stage",
        CareerStagesByPathView.as_view(),
        name="academy_career_path_id_career_stage",
    ),
    path("academy/career_path/<int:career_path_id>", CareerPathByIdView.as_view(), name="academy_career_path_id"),
    path("academy/career_path", CareerPathsView.as_view(), name="academy_career_path"),
]
