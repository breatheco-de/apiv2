from django.db import models

from breathecode.admissions.models import Academy

"""
## Example: CareerStage, Competency, Skill, StageCompetency, CompetencySkill

```python
# Create some skills
problem_solving_skill = Skill.objects.create(
    name="Problem Solving",
    description="Ability to resolve complex issues"
)
communication_skill = Skill.objects.create(
    name="Communication",
    description="Effectively convey ideas"
)


# Create a competency
competency = Competency.objects.create(
    name="Critical Thinking",
    description="Structured reasoning and analysis"
)

# Relate skills to a competency via CompetencySkill
CompetencySkill.objects.create(
    competency=competency,
    skill=problem_solving_skill,
    weight=70
)
CompetencySkill.objects.create(
    competency=competency,
    skill=communication_skill,
    weight=30
)

# Create a career stage
stage = CareerStage.objects.create(
    name="Junior",
    description="Entry-level position"
)

# Relate competency to stage with required proficiency and is_core flag
StageCompetency.objects.create(
    stage=stage,
    competency=competency,
    required_level=StageCompetency.RequiredLevel.FOUNDATION,
    is_core=True
)
```
"""



class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        abstract = True


class JobFamily(TimeStampedModel):
    slug = models.SlugField(max_length=150, unique=True)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    academy = models.ForeignKey(
        Academy,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="talent_job_families",
        help_text="Academy that owns this family, if None, it can be used across multiple academies.",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("name",)
        indexes = [
            models.Index(fields=["is_active"]),
        ]
        # Note: slug field already has unique=True, so UniqueConstraint is redundant but kept for explicit naming
        constraints = [
            models.UniqueConstraint(fields=["slug"], name="uq_job_family_slug"),
        ]

    def __str__(self) -> str:
        return self.name


class JobRole(TimeStampedModel):
    slug = models.SlugField(max_length=150)
    name = models.CharField(max_length=150)
    job_family = models.ForeignKey(JobFamily, on_delete=models.CASCADE, related_name="job_roles", help_text="Job family that owns this role.")
    description = models.TextField(blank=True)
    academy = models.ForeignKey(
        Academy,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="talent_job_roles",
        help_text="Academy that owns this role. if None, it can be used across multiple academies.",
    )
    is_active = models.BooleanField(default=True)
    is_model = models.BooleanField(default=False, help_text="Model role can be used to create new roles.")

    class Meta:
        ordering = ("name",)
        indexes = [
            models.Index(fields=["is_active"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["slug"], name="uq_job_role_slug"),
        ]

    def __str__(self) -> str:
        return self.name

class CareerPath(TimeStampedModel):
    job_role = models.ForeignKey(
        JobRole, on_delete=models.CASCADE, related_name="career_paths", help_text="Anchor role for this path."
    )
    name = models.CharField(max_length=150)
    academy = models.ForeignKey(
        Academy,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="talent_career_paths",
        help_text="Academy that owns this career path.",
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("job_role__name", "name")
        constraints = [
            models.UniqueConstraint(fields=["job_role", "name"], name="uq_career_path_role_name"),
        ]

    def __str__(self) -> str:
        return f"{self.job_role.name} • {self.name}"


# Example:
#
# JobFamily:   Engineering
#   └── JobRole:   Backend Developer
#        └── CareerPath:   Backend Development Track
#             ├── CareerStage 1: Junior Backend Developer
#             ├── CareerStage 2: Mid-level Backend Developer
#             └── CareerStage 3: Senior Backend Developer
#
# JobFamily:   Product
#   └── JobRole:   Product Manager
#        └── CareerPath:   Product Management Track
#             ├── CareerStage 1: Associate Product Manager
#             ├── CareerStage 2: Product Manager
#             └── CareerStage 3: Senior Product Manager
#
# JobFamily:   Design
#   └── JobRole:   UX Designer
#        └── CareerPath:   UX Design Track
#             ├── CareerStage 1: Junior UX Designer
#             ├── CareerStage 2: UX Designer
#             └── CareerStage 3: Lead UX Designer


class CareerStage(TimeStampedModel):
    career_path = models.ForeignKey(
        CareerPath, on_delete=models.CASCADE, related_name="stages", help_text="Career path that owns this stage."
    )
    sequence = models.PositiveSmallIntegerField(help_text="Position within the career path.")
    title = models.CharField(max_length=150)
    goal = models.TextField(blank=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ("career_path", "sequence")
        constraints = [
            models.UniqueConstraint(fields=["career_path", "sequence"], name="uq_stage_path_sequence"),
        ]
        indexes = [
            models.Index(fields=["career_path", "sequence"]),
        ]

    def __str__(self) -> str:
        return f"{self.career_path.name} • {self.title}"


# Example Competencies with Stages:
# Junior Backend Developer (stage):
#   - competency: python          # name: Python Programming
#   - competency: teamwork        # name: Teamwork
# Mid-level Backend Developer (stage):
#   - competency: python          # name: Python Programming
#   - competency: sql             # name: SQL Databases
#   - competency: communication   # name: Communication
# Senior Backend Developer (stage):
#   - competency: leadership      # name: Leadership
#   - competency: project_mgmt    # name: Project Management
#   - competency: python          # name: Python Programming

# Competencies are not related to an academy, they can be used across multiple academies.
class Competency(TimeStampedModel):
    class Type(models.TextChoices):
        TECHNICAL = "technical", "Technical"
        BEHAVIORAL = "behavioral", "Behavioral"
        LEADERSHIP = "leadership", "Leadership"
        FUNCTIONAL = "functional", "Functional"

    slug = models.SlugField(max_length=150, unique=True)
    name = models.CharField(max_length=150)
    type = models.CharField(max_length=20, choices=Type.choices, default=Type.TECHNICAL)
    description = models.TextField(blank=True)
    technologies = models.CharField(
        max_length=500,
        blank=True,
        help_text="Comma-separated string of technologies (e.g., 'Python, Django, PostgreSQL')."
    )

    class Meta:
        ordering = ("name",)
        # Note: slug field already has unique=True, so UniqueConstraint is redundant but kept for explicit naming
        constraints = [
            models.UniqueConstraint(fields=["slug"], name="uq_competency_slug"),
        ]

    def __str__(self) -> str:
        return self.name


# Difference between Skill and Competency:
# - A skill is a specific, teachable ability or proficiency (e.g., "Python", "SQL", "React").
# - A competency is a broader capability that combines relevant skills, knowledge, and behaviors required to perform a role or function effectively (e.g., "Python Programming" competency may require several skills like Python syntax, using virtualenv, writing unit tests).

# SkillDomain represents the category or domain that a skill belongs to (e.g., Programming, Database, Frontend, Soft Skill).
# Skill domains are not related to an academy, they can be used across multiple academies.
class SkillDomain(TimeStampedModel):
    slug = models.SlugField(max_length=150, unique=True)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ("name",)
        # Note: slug field already has unique=True, so UniqueConstraint is redundant but kept for explicit naming
        constraints = [
            models.UniqueConstraint(fields=["slug"], name="uq_skill_domain_slug"),
        ]

    def __str__(self) -> str:
        return self.name


# Example Skills (each with domain and linked competency):
# - skill: python             # name: Python, domain: programming, competency: python_programming
# - skill: sql                # name: SQL, domain: database, competency: sql_databases
# - skill: react              # name: React, domain: frontend, competency: frontend_frameworks
# - skill: teamwork           # name: Teamwork, domain: soft_skill, competency: teamwork
# - skill: rest_api           # name: REST API, domain: programming, competency: api_design

# skills are not related to an academy, they can be used across multiple academies.
class Skill(TimeStampedModel):
    slug = models.SlugField(max_length=150, unique=True)
    name = models.CharField(max_length=150)
    domain = models.ForeignKey(
        SkillDomain,
        on_delete=models.CASCADE,
        related_name="skills",
        help_text="Domain that categorizes this skill.",
    )
    description = models.TextField(blank=True)
    technologies = models.CharField(
        max_length=500,
        blank=True,
        help_text="Comma-separated string of technologies (e.g., 'Python, Django, PostgreSQL')."
    )

    class Meta:
        ordering = ("name",)
        # Note: slug field already has unique=True, so UniqueConstraint is redundant but kept for explicit naming
        constraints = [
            models.UniqueConstraint(fields=["slug"], name="uq_skill_slug"),
        ]

    def __str__(self) -> str:
        return self.name

class StageCompetency(TimeStampedModel):
    class RequiredLevel(models.TextChoices):
        FOUNDATION = "foundation", "Foundation"
        CORE = "core", "Core"
        APPLIED = "applied", "Applied"

    stage = models.ForeignKey(
        CareerStage, on_delete=models.CASCADE, related_name="stage_competencies", help_text="Stage that requires this competency."
    )
    competency = models.ForeignKey(
        Competency, on_delete=models.CASCADE, related_name="stage_assignments", help_text="Competency required at this stage."
    )
    required_level = models.CharField(max_length=15, choices=RequiredLevel.choices, default=RequiredLevel.CORE)
    is_core = models.BooleanField(default=True, help_text="Mark as False for optional competencies.")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["stage", "competency"], name="uq_stage_competency"),
        ]
        indexes = [
            models.Index(fields=["stage", "competency"]),
        ]

    def __str__(self) -> str:
        return f"{self.stage} • {self.competency}"

class CompetencySkill(TimeStampedModel):
    competency = models.ForeignKey(
        Competency, on_delete=models.CASCADE, related_name="competency_skills", help_text="Parent competency."
    )
    skill = models.ForeignKey(
        Skill, on_delete=models.CASCADE, related_name="skill_competencies", help_text="Skill contributing to the competency."
    )
    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Optional relative weight (0-100) describing the skill impact.",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["competency", "skill"], name="uq_competency_skill"),
        ]
        indexes = [
            models.Index(fields=["competency", "skill"]),
        ]

    def __str__(self) -> str:
        return f"{self.competency} • {self.skill}"



class SkillBehaviorIndicator(TimeStampedModel):
    class Level(models.TextChoices):
        FOUNDATION = "foundation", "Foundation"
        CORE = "core", "Core"
        APPLIED = "applied", "Applied"

    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="behavioral_indicators")
    level = models.CharField(max_length=15, choices=Level.choices)
    description = models.TextField(
        help_text="Observable behavior that shows this skill at the given level."
    )

    class Meta:
        ordering = ("skill", "level")

class SkillKnowledgeItem(TimeStampedModel):
    skill = models.ForeignKey(
        Skill,
        on_delete=models.CASCADE,
        related_name="knowledge_items"
    )
    description = models.TextField(
        help_text="Concept, fact, or principle a learner must understand to perform the skill."
    )

    class Meta:
        ordering = ("skill", "id")

class SkillAttitudeTag(TimeStampedModel):
    skill = models.ForeignKey(
        Skill,
        on_delete=models.CASCADE,
        related_name="attitude_tags"
    )
    tag = models.CharField(
        max_length=150,
        help_text="Short mindset/attitude label (e.g., 'attention to detail')."
    )
    description = models.TextField(
        blank=True,
        help_text="Optional elaboration of the attitude."
    )

    class Meta:
        ordering = ("skill", "tag")