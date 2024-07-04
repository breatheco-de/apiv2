import logging
from django.contrib import admin
from .models import (
    Platform,
    ZyteProject,
    Spider,
    Job,
    Employer,
    Position,
    PositionAlias,
    CareerTag,
    Location,
    LocationAlias,
)

logger = logging.getLogger(__name__)


# Register your models here.
@admin.register(Platform)
class PlatformAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at")


@admin.display(description="Fetch sync all data.")
def fetch_sync_all_data_admin(modeladmin, request, queryset):
    from django.contrib import messages
    from .actions import fetch_sync_all_data

    spiders = queryset.all()
    try:
        for s in spiders:
            fetch_sync_all_data(s)
            messages.success(request, f"{s.sync_desc}")
    except Exception as e:
        logger.error(f"There was an error retriving the spider {str(e)}")
        messages.error(request, f"There was an error retriving the spider {str(e)}")


@admin.display(description="Run spider.")
def run_spider_admin(modeladmin, request, queryset):
    from django.contrib import messages
    from .actions import run_spider

    spiders = queryset.all()
    try:
        for s in spiders:
            run_spider(s)
            messages.success(request, f"The execution of the spider {s} was successful")
    except Exception as e:
        message = f"There was an error retriving the spider {str(e)}"
        logger.error(message)
        messages.error(request, message)


@admin.display(description="Get was publiched date.")
def get_was_published_date_from_string_admin(modeladmin, request, queryset):
    from django.contrib import messages
    from .actions import get_was_published_date_from_string

    jobs = queryset.all()
    try:
        for job in jobs:
            get_was_published_date_from_string(job)
        messages.success(request, "The publication date was successfully parsed")
    except Exception as e:
        logger.error(f"There was an error retriving the jobs {str(e)}")
        messages.error(request, f"There was an error retriving the jobs {str(e)}")


@admin.register(Spider)
class SpiderAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "job_search",
        "position",
        "spider_last_run_status",
        "spider_last_run_desc",
        "sync_status",
        "sync_desc",
        "zyte_last_fetch_date",
    )
    actions = (
        fetch_sync_all_data_admin,
        run_spider_admin,
    )


@admin.register(ZyteProject)
class ZyteProjectAdmin(admin.ModelAdmin):
    list_display = ("platform", "zyte_api_key", "zyte_api_deploy", "created_at")


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "spider",
        "published_date_raw",
        "salary",
        "status",
        "employer",
        "position",
        "apply_url",
        "currency",
        "remote",
        "created_at",
    )
    actions = (get_was_published_date_from_string_admin,)


@admin.register(Employer)
class EmployerAdmin(admin.ModelAdmin):
    list_display = ("name", "location", "created_at")


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at")


@admin.register(PositionAlias)
class PositionAliasAdmin(admin.ModelAdmin):
    list_display = ("name", "position", "created_at")


@admin.register(CareerTag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("slug", "created_at")


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at")


@admin.register(LocationAlias)
class LocationAliasAdmin(admin.ModelAdmin):
    list_display = ("name", "location", "created_at")
