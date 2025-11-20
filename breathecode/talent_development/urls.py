from django.urls import path

from .views import (
    CareerPathsView,
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
    SkillDomainsView,
    SkillKnowledgeItemsView,
    SkillsView,
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
    path("academy/competency", CompetenciesView.as_view(), name="academy_competency"),
    path("academy/competency/<int:competency_id>", CompetencyByIdView.as_view(), name="academy_competency_id"),
    path("academy/competency/<str:competency_slug>", CompetencyBySlugView.as_view(), name="academy_competency_slug"),
    path("academy/skill_domain", SkillDomainsView.as_view(), name="academy_skill_domain"),
    path("academy/skill_knowledge_item", SkillKnowledgeItemsView.as_view(), name="academy_skill_knowledge_item"),
    path("academy/skill_attitude_tag", SkillAttitudeTagsView.as_view(), name="academy_skill_attitude_tag"),
    # Career Path endpoints
    path("academy/career_path", CareerPathsView.as_view(), name="academy_career_path"),
]

