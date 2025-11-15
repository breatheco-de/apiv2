from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        abstract = True


class JobFamily(TimeStampedModel):
    slug = models.SlugField(max_length=150, unique=True)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("name",)
        indexes = [
            models.Index(fields=["is_active"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["slug"], name="uq_job_family_slug"),
        ]

    def __str__(self) -> str:
        return self.name


class JobRole(TimeStampedModel):
    slug = models.SlugField(max_length=150, unique=True)
    name = models.CharField(max_length=150)
    job_family = models.ForeignKey(JobFamily, on_delete=models.CASCADE, related_name="job_roles", help_text="Job family that owns this role.")
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

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
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("job_role__name", "name")
        constraints = [
            models.UniqueConstraint(fields=["job_role", "name"], name="uq_career_path_role_name"),
        ]

    def __str__(self) -> str:
        return f"{self.job_role.name} • {self.name}"


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

    class Meta:
        ordering = ("name",)
        constraints = [
            models.UniqueConstraint(fields=["slug"], name="uq_competency_slug"),
        ]
    def __str__(self) -> str:
        return self.name


class Skill(TimeStampedModel):
    class Category(models.TextChoices):
        PROGRAMMING = "programming", "Programming"
        DATABASE = "database", "Database"
        FRONTEND = "frontend", "Frontend"
        SOFT_SKILL = "soft_skill", "Soft Skill"

    slug = models.SlugField(max_length=150, unique=True)
    name = models.CharField(max_length=150)
    category = models.CharField(max_length=20, choices=Category.choices)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ("name",)
        constraints = [
            models.UniqueConstraint(fields=["slug"], name="uq_skill_slug"),
        ]
    def __str__(self) -> str:
        return self.name

class StageCompetency(TimeStampedModel):
    class RequiredLevel(models.TextChoices):
        FOUNDATION = "foundation", "Foundation"
        WORKING = "working", "Working"
        ADVANCED = "advanced", "Advanced"
        EXPERT = "expert", "Expert"

    stage = models.ForeignKey(
        CareerStage, on_delete=models.CASCADE, related_name="stage_competencies", help_text="Stage that requires this competency."
    )
    competency = models.ForeignKey(
        Competency, on_delete=models.CASCADE, related_name="stage_assignments", help_text="Competency required at this stage."
    )
    required_level = models.CharField(max_length=15, choices=RequiredLevel.choices)
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


