import logging
from django.contrib import admin
from django.contrib import messages
from .models import Platform, ZyteProject, Spider, Job, Employer, Position, PositionAlias, Tag, Location, LocationAlias
from .actions import fetch_sync_all_data, run_spider, parse_date

logger = logging.getLogger(__name__)


# Register your models here.
@admin.register(Platform)
class PlatformAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')


def fetch_sync_all_data_admin(modeladmin, request, queryset):
    from django.contrib import messages
    from .actions import fetch_sync_all_data
    spiders = queryset.all()
    try:
        for s in spiders:
            fetch_sync_all_data(s)
            messages.success(request, f'{s.sync_desc}')
    except Exception as e:
        logger.error(f'There was an error retriving the spider {str(e)}')
        messages.error(request, f'There was an error retriving the spider {str(e)}')


def run_spider_admin(modeladmin, request, queryset):
    from django.contrib import messages
    from .actions import run_spider
    spiders = queryset.all()
    try:
        for s in spiders:
            run_spider(s)
            messages.success(request, f'The execution of the spider {s} was successful')
    except Exception as e:
        message = f'There was an error retriving the jobs {str(e)}'
        logger.error(message)
        messages.error(request, message)


def parse_date_admin(modeladmin, request, queryset):
    from django.contrib import messages
    from .actions import parse_date
    jobs = queryset.all()
    try:
        for job in jobs:
            parse_date(job)
    except Exception as e:
        logger.error(f'There was an error retriving the jobs {str(e)}')
        messages.error(request, f'There was an error retriving the jobs {str(e)}')


fetch_sync_all_data_admin.short_description = 'Fetch sync all data.'
run_spider_admin.short_description = 'Run spider.'
parse_date_admin.short_description = 'Parse date.'


@admin.register(Spider)
class SpiderAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'sync_desc', 'zyte_last_fetch_date')
    actions = (
        fetch_sync_all_data_admin,
        run_spider_admin,
    )


@admin.register(ZyteProject)
class ZyteProjectAdmin(admin.ModelAdmin):
    list_display = ('platform', 'zyte_api_key', 'zyte_api_deploy', 'created_at')


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('title', 'platform', 'published_date_raw', 'salary', 'status', 'employer', 'position',
                    'apply_url', 'currency', 'remote', 'created_at')
    actions = (parse_date_admin, )


@admin.register(Employer)
class EmployerAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'created_at')


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')


@admin.register(PositionAlias)
class PositionAliasAdmin(admin.ModelAdmin):
    list_display = ('name', 'position', 'created_at')


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('slug', 'created_at')


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')


@admin.register(LocationAlias)
class LocationAliasAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'created_at')
