import logging
from django.contrib import admin, messages
from django.utils.html import format_html
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from breathecode.admissions.admin import CohortAdmin
from .models import Asset, AssetTranslation, AssetTechnology, AssetAlias
from .tasks import async_sync_with_github
from .actions import sync_with_github

logger = logging.getLogger(__name__)


def add_gitpod(modeladmin, request, queryset):
    assets = queryset.update(gitpod=True)


add_gitpod.short_description = "Add GITPOD"


def remove_gitpod(modeladmin, request, queryset):
    assets = queryset.update(gitpod=False)


remove_gitpod.short_description = "Remove GITPOD"


def make_external(modeladmin, request, queryset):
    result = queryset.update(external=True)


make_external.short_description = "Make it an EXTERNAL resource (new window)"


def make_internal(modeladmin, request, queryset):
    result = queryset.update(external=False)


make_internal.short_description = "Make it an INTERNAL resource"


def sync_github(modeladmin, request, queryset):
    assets = queryset.all()
    for a in assets:
        async_sync_with_github.delay(a.slug, request.user.id)
        # sync_with_github(a.slug, request.user.id)


sync_github.short_description = "Sync With Github"


def author_aalejo(modeladmin, request, queryset):
    assets = queryset.all()
    for a in assets:
        a.author = request.user
        a.save()
        # sync_with_github(a.slug, request.user.id)


author_aalejo.short_description = "Make myself the author of these assets"


# Register your models here.
@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    search_fields = ['title', 'slug', 'author__email', 'url']
    list_display = ('slug', 'title', 'current_status', 'lang', 'asset_type',
                    'url_path')
    list_filter = ['asset_type', 'lang']
    actions = [add_gitpod, remove_gitpod, sync_github, author_aalejo]

    def url_path(self, obj):
        return format_html(
            f"<a rel='noopener noreferrer' target='_blank' href='{obj.url}'>open</a>"
        )

    def current_status(self, obj):
        colors = {
            "OK": "bg-success",
            "ERROR": "bg-error",
            "WARNING": "bg-warning",
            "DRAFT": "",
        }
        return format_html(
            f"<span class='badge {colors[obj.status]}'>{obj.status}</span>")


# Register your models here.
@admin.register(AssetTranslation)
class AssetTranslationsAdmin(admin.ModelAdmin):
    search_fields = ['title', 'slug']
    list_display = ('slug', 'title')


# Register your models here.
@admin.register(AssetTechnology)
class AssetTechnologyAdmin(admin.ModelAdmin):
    search_fields = ['title', 'slug']
    list_display = ('slug', 'title')


# Register your models here.
@admin.register(AssetAlias)
class AssetAliasAdmin(admin.ModelAdmin):
    search_fields = ['slug', 'asset']
    list_display = ('slug', 'asset')
