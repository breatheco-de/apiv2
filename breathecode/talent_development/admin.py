from django.contrib import admin

from . import models


class CareerPathInline(admin.TabularInline):
    model = models.CareerPath
    extra = 0
    fields = ("name", "is_active")
    show_change_link = True


class JobRoleInline(admin.TabularInline):
    model = models.JobRole
    extra = 0
    fields = ("name", "is_active")
    show_change_link = True


@admin.register(models.JobFamily)
class JobFamilyAdmin(admin.ModelAdmin):
    list_display = ("name", "academy", "is_active", "updated_at")
    list_filter = ("is_active", "academy")
    search_fields = ("name", "description")
    ordering = ("name",)
    readonly_fields = ("created_at", "updated_at")
    inlines = (JobRoleInline,)
    fieldsets = (
        (None, {"fields": ("name", "slug", "academy", "description", "is_active")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )


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
    list_display = ("name", "job_role", "is_active", "updated_at")
    list_filter = ("is_active", "job_role__job_family")
    search_fields = ("name", "description", "job_role__name")
    ordering = ("job_role__name", "name")
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
    list_filter = ("career_path__job_role__job_family",)
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


@admin.register(models.SkillDomain)
class SkillDomainAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "updated_at")
    search_fields = ("name", "slug", "description")
    readonly_fields = ("created_at", "updated_at")


@admin.register(models.Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ("name", "domain", "updated_at")
    list_filter = ("domain",)
    search_fields = ("name", "description")
    autocomplete_fields = ("domain",)
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



