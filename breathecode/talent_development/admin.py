from django.contrib import admin

from . import models


class CareerPathInline(admin.TabularInline):
    model = models.CareerPath
    extra = 0
    fields = ("name", "is_active")
    show_change_link = True


@admin.register(models.JobRole)
class JobRoleAdmin(admin.ModelAdmin):
    list_display = ("name", "job_family", "is_active", "updated_at")
    list_filter = ("job_family", "is_active")
    search_fields = ("name", "job_family")
    inlines = (CareerPathInline,)
    ordering = ("name",)
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("name", "job_family", "description", "is_active")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )


class CareerStageInline(admin.TabularInline):
    model = models.CareerStage
    extra = 0
    fields = ("sequence", "title")
    ordering = ("sequence",)
    show_change_link = True


@admin.register(models.CareerPath)
class CareerPathAdmin(admin.ModelAdmin):
    list_display = ("name", "role", "is_active", "updated_at")
    list_filter = ("is_active", "role__job_family")
    search_fields = ("name", "description", "role__name")
    ordering = ("role__name", "name")
    inlines = (CareerStageInline,)
    readonly_fields = ("created_at", "updated_at")


class StageCompetencyInline(admin.TabularInline):
    model = models.StageCompetency
    extra = 0
    autocomplete_fields = ("competency",)
    fields = ("competency", "required_level", "is_core")


@admin.register(models.CareerStage)
class CareerStageAdmin(admin.ModelAdmin):
    list_display = ("title", "career_path", "sequence", "updated_at")
    list_filter = ("career_path__role__job_family",)
    search_fields = ("title", "goal", "career_path__name")
    ordering = ("career_path", "sequence")
    readonly_fields = ("created_at", "updated_at")
    inlines = (StageCompetencyInline,)


class CompetencySkillInline(admin.TabularInline):
    model = models.CompetencySkill
    extra = 0
    autocomplete_fields = ("skill",)
    fields = ("skill", "weight")


@admin.register(models.Competency)
class CompetencyAdmin(admin.ModelAdmin):
    list_display = ("name", "type", "updated_at")
    list_filter = ("type",)
    search_fields = ("name", "description")
    inlines = (CompetencySkillInline,)
    readonly_fields = ("created_at", "updated_at")


class ModuleSkillInline(admin.TabularInline):
    model = models.ModuleSkill
    extra = 0
    autocomplete_fields = ("skill",)
    fields = ("skill", "weight")


@admin.register(models.LearningModule)
class LearningModuleAdmin(admin.ModelAdmin):
    list_display = ("name", "learnpack_slug", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name", "learnpack_slug", "description")
    readonly_fields = ("created_at", "updated_at")
    inlines = (ModuleSkillInline,)


@admin.register(models.Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "updated_at")
    list_filter = ("category",)
    search_fields = ("name", "description")
    readonly_fields = ("created_at", "updated_at")


@admin.register(models.StageCompetency)
class StageCompetencyAdmin(admin.ModelAdmin):
    list_display = ("stage", "competency", "required_level", "is_core")
    list_filter = ("required_level", "is_core", "stage__career_path")
    autocomplete_fields = ("stage", "competency")
    search_fields = ("stage__title", "competency__name")
    readonly_fields = ("created_at", "updated_at")


@admin.register(models.CompetencySkill)
class CompetencySkillAdmin(admin.ModelAdmin):
    list_display = ("competency", "skill", "weight")
    autocomplete_fields = ("competency", "skill")
    search_fields = ("competency__name", "skill__name")
    readonly_fields = ("created_at", "updated_at")


@admin.register(models.ModuleSkill)
class ModuleSkillAdmin(admin.ModelAdmin):
    list_display = ("module", "skill", "weight")
    autocomplete_fields = ("module", "skill")
    search_fields = ("module__name", "skill__name")
    readonly_fields = ("created_at", "updated_at")

