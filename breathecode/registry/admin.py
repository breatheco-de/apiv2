import logging, re, html
from django.contrib import admin, messages
from django.utils.html import format_html
from django.contrib.auth.models import User
from django.db.models import Q
from django.forms import model_to_dict
from django import forms
from django.contrib.auth.admin import UserAdmin
from breathecode.admissions.admin import CohortAdmin
from breathecode.assessment.models import Assessment
from breathecode.assessment.actions import create_from_json
from breathecode.utils.admin import change_field
from .models import Asset, AssetTechnology, AssetAlias, AssetErrorLog, KeywordCluster, AssetCategory, AssetKeyword
from .tasks import async_pull_from_github, async_test_asset
from .actions import pull_from_github, get_user_from_github_username, test_asset

logger = logging.getLogger(__name__)
lang_flags = {
    'en': '🇺🇸',
    'us': '🇺🇸',
    'es': '🇪🇸',
    'it': '🇮🇹',
    None: '',
}


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


def pull_content_from_github(modeladmin, request, queryset):
    queryset.update(sync_status='PENDING', status_text='Starting to sync...')
    assets = queryset.all()
    for a in assets:
        async_pull_from_github.delay(a.slug, request.user.id)
        # pull_from_github(a.slug)  # uncomment for testing purposes


def make_me_author(modeladmin, request, queryset):
    assets = queryset.all()
    for a in assets:
        a.author = request.user
        a.save()


def get_author_grom_github_usernames(modeladmin, request, queryset):
    assets = queryset.all()
    for a in assets:
        authors = get_user_from_github_username(a.authors_username)
        if len(authors) > 0:
            a.author = authors.pop()
            a.save()


def make_me_owner(modeladmin, request, queryset):
    assets = queryset.all()
    for a in assets:
        a.owner = request.user
        a.save()


def remove_dot_from_slug(modeladmin, request, queryset):
    assets = queryset.all()
    for a in assets:
        if '.' in a.slug:
            a.slug = a.slug.replace('.', '-')
            a.save()


def generate_spanish_translation(modeladmin, request, queryset):
    assets = queryset.all()
    for old in assets:
        old_id = old.id
        if old.lang not in ['us', 'en']:
            messages.error(request,
                           f'Error in {old.slug}: Can only generate trasnlations for english lessons')
            continue

        new_asset = old.all_translations.filter(
            Q(lang='es') | Q(slug=old.slug + '-es')
            | Q(slug=old.slug + '.es')).first()
        if new_asset is not None:
            messages.error(request, f'Translation to {old.slug} already exists with {new_asset.slug}')
            if '.es' in new_asset.slug:
                new_asset.slug = new_asset.slug.split('.')[0] + '-es'
                new_asset.save()

        else:
            new_asset = old
            new_asset.pk = None
            new_asset.lang = 'es'
            new_asset.sync_status = 'PENDING'
            new_asset.status_text = 'Translation generated, waiting for sync'
            new_asset.slug = old.slug + '-es'
            new_asset.save()

        old = Asset.objects.get(id=old_id)
        old.all_translations.add(new_asset)
        for t in old.all_translations.all():
            new_asset.all_translations.add(t)
        for t in old.technologies.all():
            new_asset.technologies.add(t)


def test_asset_integrity(modeladmin, request, queryset):
    queryset.update(test_status='PENDING')
    assets = queryset.all()

    for a in assets:
        try:
            async_test_asset.delay(a.slug)
            #test_asset(a)
        except Exception as e:
            messages.error(request, a.slug + ': ' + str(e))


def create_assessment_from_asset(modeladmin, request, queryset):
    queryset.update(test_status='PENDING')
    assets = queryset.all()

    for a in assets:
        try:
            if a.asset_type != 'QUIZ':
                raise Exception(f'Can\'t create assessment from {a.asset_type.lower()}, only quiz.')
            ass = Assessment.objects.filter(slug=a.slug).first()
            if ass is not None:
                raise Exception(f'Assessment with slug {a.slug} already exists, try a different slug?')

            if a.config is None or a.config == '':
                raise Exception(f'Assessment with slug {a.slug} has no config')

            create_from_json(a.config, slug=a.slug)
        except Exception as e:
            messages.error(request, a.slug + ': ' + str(e))


class AssessmentFilter(admin.SimpleListFilter):

    title = 'Associated Assessment'

    parameter_name = 'has_assessment'

    def lookups(self, request, model_admin):

        return (
            ('yes', 'Has assessment'),
            ('no', 'No assessment'),
        )

    def queryset(self, request, queryset):

        if self.value() == 'yes':
            return queryset.filter(assessment__isnull=False)

        if self.value() == 'no':
            return queryset.filter(assessment__isnull=True)


class AssetForm(forms.ModelForm):
    class Meta:
        model = Asset
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(AssetForm, self).__init__(*args, **kwargs)
        self.fields['all_translations'].queryset = Asset.objects.filter(
            asset_type=self.instance.asset_type).order_by('slug')  # or something else
        self.fields['technologies'].queryset = AssetTechnology.objects.all().order_by(
            'slug')  # or something else


# Register your models here.
@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    form = AssetForm
    search_fields = ['title', 'slug', 'author__email', 'url']
    list_display = ('main', 'current_status', 'alias', 'techs', 'url_path')
    list_filter = ['asset_type', 'status', 'sync_status', 'test_status', 'lang', 'external', AssessmentFilter]
    raw_id_fields = ['author', 'owner']
    actions = [
        test_asset_integrity,
        add_gitpod,
        remove_gitpod,
        pull_content_from_github,
        make_me_author,
        make_me_owner,
        create_assessment_from_asset,
        get_author_grom_github_usernames,
        generate_spanish_translation,
        remove_dot_from_slug,
    ] + change_field(['DRAFT', 'UNNASIGNED', 'OK'], name='status') + change_field(['us', 'es'], name='lang')

    def get_form(self, request, obj=None, **kwargs):

        if obj is not None and obj.readme is not None and 'ipynb' in obj.url and len(obj.readme) > 2000:
            self.exclude = ('readme', 'html')
        form = super(AssetAdmin, self).get_form(request, obj, **kwargs)
        return form

    def url_path(self, obj):
        return format_html(f"""
            <a rel='noopener noreferrer' target='_blank' href='{obj.url}'>github</a> |
            <a rel='noopener noreferrer' target='_blank' href='/v1/registry/asset/preview/{obj.slug}'>preview</a>
        """)

    def main(self, obj):

        return format_html(f'''
                <p style="border: 1px solid #BDBDBD; border-radius: 3px; font-size: 10px; padding: 3px;margin: 0;">{lang_flags[obj.lang]} {obj.asset_type}</p>
                <p style="margin: 0; padding: 0;">{obj.slug}</p>
                <p style="color: white; font-size: 10px;margin: 0; padding: 0;">{obj.title}</p>
            ''')

    def current_status(self, obj):
        colors = {
            'PUBLISHED': 'bg-success',
            'OK': 'bg-success',
            'ERROR': 'bg-error',
            'WARNING': 'bg-warning',
            None: 'bg-warning',
            'DRAFT': 'bg-error',
            'PENDING_TRANSLATION': 'bg-error',
            'PENDING': 'bg-warning',
            'WARNING': 'bg-warning',
            'UNASSIGNED': 'bg-error',
            'UNLISTED': 'bg-warning',
        }

        def from_status(s):
            if s in colors:
                return colors[s]
            return ''

        status = 'No status'
        if obj.status_text is not None:
            status = re.sub(r'[^\w\._\-]', ' ', obj.status_text)
        return format_html(
            f"""<table style='max-width: 200px;'><tr><td style='font-size: 10px !important;'>Publish</td><td style='font-size: 10px !important;'>Synch</td><td style='font-size: 10px !important;'>Test</td></tr>
        <td><span class='badge {from_status(obj.status)}'>{obj.status}</span></td>
        <td><span class='badge {from_status(obj.sync_status)}'>{obj.sync_status}</span></td>
        <td><span class='badge {from_status(obj.test_status)}'>{obj.test_status}</span></td>
        <tr><td colspan='3'>{status}</td></tr>
        </table>""")

    def techs(self, obj):
        return ', '.join([t.slug for t in obj.technologies.all()])

    def alias(self, obj):
        aliases = AssetAlias.objects.filter(asset__all_translations__slug=obj.slug)
        return format_html(''.join([
            f'<span style="display: inline-block; background: #2d302d; padding: 2px; border-radius: 3px; margin: 2px;">{lang_flags[a.asset.lang]}{a.slug}</span>'
            for a in aliases
        ]))


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


@admin.register(AssetAlias)
class AssetAliasAdmin(admin.ModelAdmin):
    search_fields = ['slug']
    list_display = ('slug', 'asset', 'created_at')
    list_filter = [
        'asset__asset_type', 'asset__status', 'asset__sync_status', 'asset__test_status', 'asset__lang',
        'asset__external'
    ]
    raw_id_fields = ['asset']


def make_alias(modeladmin, request, queryset):
    errors = queryset.all()
    for e in errors:
        if e.slug != AssetErrorLog.SLUG_NOT_FOUND:
            messages.error(
                request,
                f'Error: You can only make alias for {AssetErrorLog.SLUG_NOT_FOUND} errors and it was {e.slug}'
            )

        if e.asset is None:
            messages.error(
                request,
                f'Error: Cannot make alias to fix error {e.slug} ({e.id}), please assign asset before trying to fix it'
            )

        else:
            alias = AssetAlias.objects.filter(slug=e.path).first()
            if alias is None:
                alias = AssetAlias(slug=e.path, asset=e.asset)
                alias.save()
                AssetErrorLog.objects.filter(slug=e.slug,
                                             asset_type=e.asset_type,
                                             status='ERROR',
                                             path=e.path,
                                             asset=e.asset).update(status='FIXED')
                continue

            if alias.asset.id != e.asset.id:
                messages.error(
                    request, f'Slug {e.path} already exists for a different asset {alias.asset.asset_type}')


def change_status_FIXED_including_similar(modeladmin, request, queryset):
    errors = queryset.all()
    for e in errors:
        AssetErrorLog.objects.filter(slug=e.slug, asset_type=e.asset_type, path=e.path,
                                     asset=e.asset).update(status='FIXED')


def change_status_ERROR_including_similar(modeladmin, request, queryset):
    errors = queryset.all()
    for e in errors:
        AssetErrorLog.objects.filter(slug=e.slug, asset_type=e.asset_type, path=e.path,
                                     asset=e.asset).update(status='ERROR')


def change_status_IGNORED_including_similar(modeladmin, request, queryset):
    errors = queryset.all()
    for e in errors:
        AssetErrorLog.objects.filter(slug=e.slug, asset_type=e.asset_type, path=e.path,
                                     asset=e.asset).update(status='IGNORED')


@admin.register(AssetErrorLog)
class AssetErrorLogAdmin(admin.ModelAdmin):
    search_fields = ['slug', 'user__email', 'user__first_name', 'user__last_name']
    list_display = ('slug', 'path', 'current_status', 'user', 'created_at', 'asset')
    raw_id_fields = ['user', 'asset']
    list_filter = ['status', 'slug', 'asset_type']
    actions = [
        make_alias, change_status_FIXED_including_similar, change_status_ERROR_including_similar,
        change_status_IGNORED_including_similar
    ]

    def current_status(self, obj):
        colors = {
            'FIXED': 'bg-success',
            'ERROR': 'bg-error',
            'IGNORED': '',
            None: 'bg-warning',
        }
        message = ''
        if obj.status_text is not None:
            message = html.escape(obj.status_text)
        return format_html(
            f'<span class="badge {colors[obj.status]}">{obj.slug}</span><small style="display: block;">{message}</small>'
        )


@admin.register(AssetCategory)
class AssetCategoryAdmin(admin.ModelAdmin):
    search_fields = ['slug', 'title']
    list_display = ('slug', 'title', 'academy')
    raw_id_fields = ['academy']
    list_filter = ['academy']


@admin.register(AssetKeyword)
class AssetKeywordAdmin(admin.ModelAdmin):
    search_fields = ['slug', 'title']
    list_display = ('slug', 'title', 'cluster', 'academy')
    raw_id_fields = ['academy']
    list_filter = ['academy']


@admin.register(KeywordCluster)
class KeywordClusterAdmin(admin.ModelAdmin):
    search_fields = ['slug', 'title']
    list_display = ('slug', 'title', 'academy')
    raw_id_fields = ['academy']
    list_filter = ['academy']
