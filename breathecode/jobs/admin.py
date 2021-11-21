from django.contrib import admin
from .models import Platform, Spider, Job, Employer, Position, Tag, Location
from .actions import fetch_spider_data


# Register your models here.
@admin.register(Platform)
class PlatformAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')


def fetch_spider_data_admin(modeladmin, request, queryset):
    spiders = queryset.all()
    for s in spiders:
        fetch_spider_data(s)


fetch_spider_data_admin.short_description = 'Fetch latest data.'


# Register your models here.
@admin.register(Spider)
class SpiderAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    actions = (fetch_spider_data_admin, )


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('title', 'published', 'status', 'employer', 'position', 'tag', 'apply_url', 'created_at')


@admin.register(Employer)
class EmployerAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('slug', 'created_at')


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('city', 'country', 'created_at')
