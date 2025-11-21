"""
Collections of mixins used to generate talent development models for testing
"""

from breathecode.tests.mixins.models_mixin import ModelsMixin
from mixer.backend.django import mixer
from .utils import is_valid, create_models, just_one, get_list


class TalentDevelopmentModelsMixin(ModelsMixin):

    def generate_talent_development_models(
        self,
        skill_domain=False,
        skill=False,
        competency=False,
        competency_skill=False,
        job_family=False,
        job_role=False,
        career_path=False,
        career_stage=False,
        stage_competency=False,
        skill_behavior_indicator=False,
        skill_knowledge_item=False,
        skill_attitude_tag=False,
        skill_domain_kwargs={},
        skill_kwargs={},
        competency_kwargs={},
        competency_skill_kwargs={},
        job_family_kwargs={},
        job_role_kwargs={},
        career_path_kwargs={},
        career_stage_kwargs={},
        stage_competency_kwargs={},
        skill_behavior_indicator_kwargs={},
        skill_knowledge_item_kwargs={},
        skill_attitude_tag_kwargs={},
        models={},
        **kwargs,
    ):
        """Generate talent development models"""
        models = models.copy()

        # SkillDomain - no dependencies
        if not "skill_domain" in models and (is_valid(skill_domain) or is_valid(skill)):
            kargs = {}

            models["skill_domain"] = create_models(
                skill_domain, "talent_development.SkillDomain", **{**kargs, **skill_domain_kwargs}
            )

        # Skill - depends on SkillDomain
        if not "skill" in models and is_valid(skill):
            kargs = {}

            if "skill_domain" in models:
                kargs["domain"] = just_one(models["skill_domain"])

            models["skill"] = create_models(skill, "talent_development.Skill", **{**kargs, **skill_kwargs})

        # Competency - no dependencies
        if not "competency" in models and (
            is_valid(competency) or is_valid(competency_skill) or is_valid(stage_competency)
        ):
            kargs = {}

            models["competency"] = create_models(
                competency, "talent_development.Competency", **{**kargs, **competency_kwargs}
            )

        # CompetencySkill - depends on Competency and Skill
        if not "competency_skill" in models and is_valid(competency_skill):
            kargs = {}

            if "competency" in models:
                kargs["competency"] = just_one(models["competency"])

            if "skill" in models:
                kargs["skill"] = just_one(models["skill"])

            models["competency_skill"] = create_models(
                competency_skill, "talent_development.CompetencySkill", **{**kargs, **competency_skill_kwargs}
            )

        # JobFamily - no dependencies (academy can be None)
        if not "job_family" in models and (is_valid(job_family) or is_valid(job_role)):
            kargs = {}

            models["job_family"] = create_models(
                job_family, "talent_development.JobFamily", **{**kargs, **job_family_kwargs}
            )

        # JobRole - depends on JobFamily
        if not "job_role" in models and (is_valid(job_role) or is_valid(career_path)):
            kargs = {}

            if "job_family" in models:
                kargs["job_family"] = just_one(models["job_family"])

            models["job_role"] = create_models(
                job_role, "talent_development.JobRole", **{**kargs, **job_role_kwargs}
            )

        # CareerPath - depends on JobRole
        if not "career_path" in models and (is_valid(career_path) or is_valid(career_stage)):
            kargs = {}

            if "job_role" in models:
                kargs["job_role"] = just_one(models["job_role"])

            models["career_path"] = create_models(
                career_path, "talent_development.CareerPath", **{**kargs, **career_path_kwargs}
            )

        # CareerStage - depends on CareerPath
        if not "career_stage" in models and (
            is_valid(career_stage) or is_valid(stage_competency)
        ):
            kargs = {}

            if "career_path" in models:
                kargs["career_path"] = just_one(models["career_path"])

            models["career_stage"] = create_models(
                career_stage, "talent_development.CareerStage", **{**kargs, **career_stage_kwargs}
            )

        # StageCompetency - depends on CareerStage and Competency
        if not "stage_competency" in models and is_valid(stage_competency):
            kargs = {}

            if "career_stage" in models:
                kargs["stage"] = just_one(models["career_stage"])

            if "competency" in models:
                kargs["competency"] = just_one(models["competency"])

            models["stage_competency"] = create_models(
                stage_competency, "talent_development.StageCompetency", **{**kargs, **stage_competency_kwargs}
            )

        # SkillBehaviorIndicator - depends on Skill
        if not "skill_behavior_indicator" in models and is_valid(skill_behavior_indicator):
            kargs = {}

            if "skill" in models:
                kargs["skill"] = just_one(models["skill"])

            models["skill_behavior_indicator"] = create_models(
                skill_behavior_indicator,
                "talent_development.SkillBehaviorIndicator",
                **{**kargs, **skill_behavior_indicator_kwargs},
            )

        # SkillKnowledgeItem - depends on Skill
        if not "skill_knowledge_item" in models and is_valid(skill_knowledge_item):
            kargs = {}

            if "skill" in models:
                kargs["skill"] = just_one(models["skill"])

            models["skill_knowledge_item"] = create_models(
                skill_knowledge_item,
                "talent_development.SkillKnowledgeItem",
                **{**kargs, **skill_knowledge_item_kwargs},
            )

        # SkillAttitudeTag - depends on Skill
        if not "skill_attitude_tag" in models and is_valid(skill_attitude_tag):
            kargs = {}

            if "skill" in models:
                kargs["skill"] = just_one(models["skill"])

            models["skill_attitude_tag"] = create_models(
                skill_attitude_tag,
                "talent_development.SkillAttitudeTag",
                **{**kargs, **skill_attitude_tag_kwargs},
            )

        return models

