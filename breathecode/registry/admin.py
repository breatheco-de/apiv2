import logging
from django.contrib import admin, messages
from django.utils.html import format_html
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from breathecode.admissions.admin import CohortAdmin
from breathecode.utils.admin import change_field
from .models import Asset, AssetTranslation, AssetTechnology, AssetAlias
from .tasks import async_sync_with_github
from .actions import sync_with_github, get_user_from_github_username

logger = logging.getLogger(__name__)


def add_gitpod(modeladmin, request, queryset):
    assets = queryset.update(gitpod=True)


add_gitpod.short_description = 'Add GITPOD flag (to open on gitpod)'


def remove_gitpod(modeladmin, request, queryset):
    assets = queryset.update(gitpod=False)


remove_gitpod.short_description = 'Remove GITPOD flag'


def make_external(modeladmin, request, queryset):
    result = queryset.update(external=True)


make_external.short_description = 'Make it an EXTERNAL resource (new window)'


def make_internal(modeladmin, request, queryset):
    result = queryset.update(external=False)


make_internal.short_description = 'Make it an INTERNAL resource (same window)'


def sync_github(modeladmin, request, queryset):
    assets = queryset.all()
    for a in assets:
        async_sync_with_github.delay(a.slug, request.user.id)
        # sync_with_github(a.slug)  # uncomment for testing purposes


sync_github.short_description = 'Sync With Github'


def author_lesson(modeladmin, request, queryset):
    assets = queryset.all()
    for a in assets:
        a.author = request.user
        a.save()


author_lesson.short_description = 'Make myself the author of these assets'


def process_github_authors(modeladmin, request, queryset):
    assets = queryset.all()
    for a in assets:
        authors = get_user_from_github_username(a.authors_username)
        if len(authors) > 0:
            a.author = authors.pop()
            a.save()


process_github_authors.short_description = 'Get author from github usernames'


def own_lesson(modeladmin, request, queryset):
    assets = queryset.all()
    for a in assets:
        a.owner = request.user
        a.save()


own_lesson.short_description = 'Make myself the owner of these assets (github access)'


# Register your models here.
@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    search_fields = ['title', 'slug', 'author__email', 'url']
    list_display = ('slug', 'title', 'current_status', 'lang', 'asset_type', 'techs', 'url_path')
    list_filter = ['asset_type', 'status', 'lang']
    raw_id_fields = ['author', 'owner']
    actions = [add_gitpod, remove_gitpod, sync_github, author_lesson, own_lesson, process_github_authors
               ] + change_field(['DRAFT', 'UNNASIGNED', 'OK'], name='status')

    def url_path(self, obj):
        return format_html(f"<a rel='noopener noreferrer' target='_blank' href='{obj.url}'>open</a>")

    def current_status(self, obj):
        colors = {
            'PUBLISHED': 'bg-success',
            'OK': 'bg-success',
            'ERROR': 'bg-error',
            'WARNING': 'bg-warning',
            'DRAFT': 'bg-error',
            'PENDING_TRANSLATION': 'bg-error',
            'UNASSIGNED': 'bg-error',
            'UNLISTED': 'bg-warning',
        }
        return format_html(f"<span class='badge {colors[obj.status]}'>{obj.status}</span>")

    def techs(self, obj):
        return ', '.join([t.slug for t in obj.technologies.all()])


# Register your models here.
@admin.register(AssetTranslation)
class AssetTranslationsAdmin(admin.ModelAdmin):
    search_fields = ['title', 'slug']
    list_display = ('slug', 'title')


def merge_technologies(modeladmin, request, queryset):
    technologies = queryset.all()
    target_tech = None
    for t in technologies:
        # skip the first one
        if target_tech is None:
            target_tech = t
            continue

        for a in t.asset_set.all():
            a.technologies.add(target_tech)
        t.delete()


# Register your models here.
@admin.register(AssetTechnology)
class AssetTechnologyAdmin(admin.ModelAdmin):
    search_fields = ['title', 'slug']
    list_display = ('slug', 'title')
    actions = (merge_technologies, )


# Register your models here.
@admin.register(AssetAlias)
class AssetAliasAdmin(admin.ModelAdmin):
    search_fields = ['slug']
    list_display = ('slug', 'asset', 'created_at')
    raw_id_fields = ['asset']
