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
from breathecode.utils.admin import change_field
from breathecode.services.seo import SEOAnalyzer

from .models import (Asset, AssetTechnology, AssetAlias, AssetErrorLog, KeywordCluster, AssetCategory,
                     AssetKeyword, AssetComment, SEOReport, AssetImage, OriginalityScan,
                     CredentialsOriginality, SyllabusVersionProxy)
from .tasks import (async_pull_from_github, async_test_asset, async_execute_seo_report,
                    async_regenerate_asset_readme, async_download_readme_images, async_remove_img_from_cloud,
                    async_upload_image_to_bucket)
from .actions import (pull_from_github, get_user_from_github_username, test_asset, AssetThumbnailGenerator,
                      scan_asset_originality, add_syllabus_translations)

logger = logging.getLogger(__name__)
lang_flags = {
    'en': '🇺🇸',
    'us': '🇺🇸',
    'ge': '🇩🇪',
    'po': '🇵🇹',
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
        # pull_from_github(a.slug, override_meta=True)  # uncomment for testing purposes


def async_regenerate_readme(modeladmin, request, queryset):
    queryset.update(cleaning_status='PENDING', cleaning_status_details='Starting to clean...')
    assets = queryset.all()
    for a in assets:
        async_regenerate_asset_readme.delay(a.slug)


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


def async_generate_thumbnail(modeladmin, request, queryset):
    assets = queryset.all()
    for a in assets:
        generator = AssetThumbnailGenerator(a, '800', '600')
        url, permanent = generator.get_thumbnail_url()


def generate_spanish_translation(modeladmin, request, queryset):
    assets = queryset.all()
    for old in assets:
        old_id = old.id
        if old.lang not in ['us', 'en']:
            messages.error(request,
                           f'Error in {old.slug}: Can only generate trasnlations for english lessons')
            continue

        new_asset = old.all_translations.filter(
            Q(lang__iexact='es') | Q(slug__iexact=old.slug + '-es')
            | Q(slug__iexact=old.slug + '.es')).first()
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


def seo_report(modeladmin, request, queryset):
    assets = queryset.all()

    for a in assets:
        try:
            # async_execute_seo_report.delay(a.slug)
            SEOAnalyzer(a).start()
        except Exception as e:
            messages.error(request, a.slug + ': ' + str(e))


def originality_report(modeladmin, request, queryset):
    assets = queryset.all()

    for a in assets:
        try:
            # async_scan_asset_originality.delay(a.slug)
            scan_asset_originality(a)
        except Exception as e:
            raise e
            messages.error(request, a.slug + ': ' + str(e))


def seo_optimization_off(modeladmin, request, queryset):
    queryset.update(is_seo_tracked=False)


def seo_optimization_on(modeladmin, request, queryset):
    queryset.update(is_seo_tracked=True)


def load_readme_tasks(modeladmin, request, queryset):
    assets = queryset.all()
    for a in assets:
        try:
            tasks = a.get_tasks()
            print(f'{len(tasks)} tasks')
            for t in tasks:
                print(t['status'] + ': ' + t['slug'] + '\n')
        except Exception as e:
            messages.error(request, a.slug + ': ' + str(e))


def download_and_replace_images(modeladmin, request, queryset):
    assets = queryset.all()
    for a in assets:
        try:
            async_download_readme_images.delay(a.slug)
            messages.success(request, message='Asset was schedule for download')
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


class WithDescription(admin.SimpleListFilter):

    title = 'With description'

    parameter_name = 'has_description'

    def lookups(self, request, model_admin):

        return (
            ('yes', 'Has description'),
            ('no', 'No description'),
        )

    def queryset(self, request, queryset):

        if self.value() == 'yes':
            return queryset.filter(description__isnull=False)

        if self.value() == 'no':
            return queryset.filter(description__isnull=True)


class WithKeywordFilter(admin.SimpleListFilter):

    title = 'With Keyword'

    parameter_name = 'has_keyword'

    def lookups(self, request, model_admin):

        return (
            ('yes', 'Has keyword'),
            ('no', 'No keyword'),
        )

    def queryset(self, request, queryset):

        if self.value() == 'yes':
            return queryset.filter(seo_keywords__isnull=False)

        if self.value() == 'no':
            return queryset.filter(seo_keywords__isnull=True)


# Register your models here.
@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    form = AssetForm
    search_fields = ['title', 'slug', 'author__email', 'url']
    filter_horizontal = ('technologies', 'all_translations', 'seo_keywords')
    list_display = ('main', 'current_status', 'alias', 'techs', 'url_path')
    list_filter = [
        'asset_type', 'status', 'sync_status', 'test_status', 'lang', 'external', AssessmentFilter,
        WithKeywordFilter, WithDescription
    ]
    raw_id_fields = ['author', 'owner']
    actions = [
        test_asset_integrity,
        add_gitpod,
        remove_gitpod,
        pull_content_from_github,
        seo_optimization_off,
        seo_optimization_on,
        seo_report,
        originality_report,
        make_me_author,
        make_me_owner,
        get_author_grom_github_usernames,
        generate_spanish_translation,
        remove_dot_from_slug,
        load_readme_tasks,
        async_regenerate_readme,
        async_generate_thumbnail,
        download_and_replace_images,
    ] + change_field(['DRAFT', 'UNASSIGNED', 'PUBLISHED', 'OPTIMIZED'], name='status') + change_field(
        ['us', 'es'], name='lang')

    def get_form(self, request, obj=None, **kwargs):

        if obj is not None and obj.readme is not None and obj.url is not None and 'ipynb' in obj.url and len(
                obj.readme) > 2000:
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
                <p style="border: 1px solid #BDBDBD; border-radius: 3px; font-size: 10px; padding: 3px;margin: 0;">{lang_flags.get(obj.lang.lower(), None)} {obj.asset_type}</p>
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
            'OPTIMIZED': 'bg-error',
            'PENDING_TRANSLATION': 'bg-error',
            'PENDING': 'bg-warning',
            'WARNING': 'bg-warning',
            'UNASSIGNED': 'bg-error',
            'NEEDS_RESYNC': 'bg-error',
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
            f'<span style="display: inline-block; background: #2d302d; padding: 2px; border-radius: 3px; margin: 2px;">{lang_flags.get(a.asset.lang.lower(), None)}{a.slug}</span>'
            for a in aliases
        ]))


def merge_technologies(modeladmin, request, queryset):
    technologies = queryset.all()

    target_tech = technologies.filter(parent__isnull=True, featured_asset__isnull=False).first()
    if target_tech is None:
        target_tech = technologies.filter(parent__isnull=True).first()

    for t in technologies:
        # skip the first one
        if target_tech is None:
            target_tech = t
            continue

        for a in t.asset_set.all():
            a.technologies.add(target_tech)

        if t.id != target_tech.id:
            t.parent = target_tech
            t.save()


def slug_to_lower_case(modeladmin, request, queryset):
    technologies = queryset.all()

    for t in technologies:
        lowercase_tech = AssetTechnology.objects.filter(slug=t.slug.lower()).first()
        if lowercase_tech is not None:
            for a in t.asset_set.all():
                lowercase_tech.asset_set.add(a)
            t.delete()
        else:
            t.slug = t.slug.lower()
            t.save()


class ParentFilter(admin.SimpleListFilter):

    title = 'With Parent'

    parameter_name = 'has_parent'

    def lookups(self, request, model_admin):

        return (
            ('parents', 'Parents'),
            ('alias', 'Aliases'),
        )

    def queryset(self, request, queryset):

        if self.value() == 'parents':
            return queryset.filter(parent__isnull=True)

        if self.value() == 'alias':
            return queryset.filter(parent__isnull=False)


@admin.register(AssetTechnology)
class AssetTechnologyAdmin(admin.ModelAdmin):
    search_fields = ['title', 'slug']
    list_display = ('id', 'get_slug', 'title', 'parent', 'featured_asset', 'description')
    list_filter = (ParentFilter, )
    raw_id_fields = ['parent', 'featured_asset']

    actions = (merge_technologies, slug_to_lower_case)

    def get_slug(self, obj):
        parent = ''
        if obj.parent is None:
            parent = '🤰🏻'

        return format_html(parent + ' ' +
                           f'<a href="/admin/registry/assettechnology/{obj.id}/change/">{obj.slug}</a>')


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


class KeywordAssignedFilter(admin.SimpleListFilter):

    title = 'With Article'

    parameter_name = 'has_article'

    def lookups(self, request, model_admin):

        return (
            ('yes', 'Has article'),
            ('no', 'No article'),
        )

    def queryset(self, request, queryset):

        if self.value() == 'yes':
            return queryset.filter(asset__isnull=False)

        if self.value() == 'no':
            return queryset.filter(asset__isnull=True)


@admin.register(AssetKeyword)
class AssetKeywordAdmin(admin.ModelAdmin):
    search_fields = ['slug', 'title']
    list_display = ('id', 'slug', 'title', 'cluster')
    # raw_id_fields = ['academy']
    list_filter = [KeywordAssignedFilter]


@admin.register(KeywordCluster)
class KeywordClusterAdmin(admin.ModelAdmin):
    search_fields = ['slug', 'title']
    list_display = ('id', 'slug', 'title', 'academy')
    raw_id_fields = ['academy']
    list_filter = ['academy']


@admin.register(AssetComment)
class AssetCommentAdmin(admin.ModelAdmin):
    list_display = ['asset', 'text', 'author']
    search_fields = ('asset__slug', 'author__first_name', 'author__last_name', 'author__email')
    raw_id_fields = ['asset', 'author', 'owner']
    list_filter = ['asset__academy']


@admin.register(SEOReport)
class SEOReportAdmin(admin.ModelAdmin):
    list_display = ['report_type', 'created_at', 'status', 'asset']
    search_fields = ('asset__slug', 'asset__title', 'report_type')
    raw_id_fields = ['asset']
    list_filter = ['asset__academy']


@admin.register(OriginalityScan)
class OriginalityScanAdmin(admin.ModelAdmin):
    list_display = ['id', 'created_at', 'status', 'asset', 'success', 'score_original', 'score_ai']
    search_fields = ('asset__slug', 'asset__title', 'report_type')
    raw_id_fields = ['asset']
    list_filter = ['asset__academy']


@admin.register(CredentialsOriginality)
class CredentialsOriginalityAdmin(admin.ModelAdmin):
    list_display = ['id', 'academy', 'created_at', 'balance', 'last_call_at']
    search_fields = ('academy__slug', 'academy__title')
    raw_id_fields = ['academy']
    list_filter = ['academy']


def remove_image_from_bucket(modeladmin, request, queryset):
    images = queryset.all()
    for img in images:
        async_remove_img_from_cloud.delay(img.id)


def upload_image_to_bucket(modeladmin, request, queryset):
    images = queryset.all()
    for img in images:
        async_upload_image_to_bucket.delay(img.id)


@admin.register(AssetImage)
class AssetImageAdmin(admin.ModelAdmin):
    list_display = ['name', 'current_status', 'mime', 'original', 'bucket']
    search_fields = ('name', 'original_url', 'bucket_url', 'assets__slug')
    raw_id_fields = ['assets']
    list_filter = ['mime', 'assets__academy']
    actions = [remove_image_from_bucket]

    def original(self, obj):
        return format_html(f'<a href="{obj.original_url}">{obj.original_url}</a>')

    def bucket(self, obj):
        return format_html(f'<a href="{obj.bucket_url}">{obj.bucket_url}</a>')

    def current_status(self, obj):
        colors = {
            'DONE': 'bg-success',
            'OK': 'bg-success',
            'PENDING': 'bg-warning',
            'WARNING': 'bg-warning',
            'ERROR': 'bg-error',
            'NEEDS_RESYNC': 'bg-error',
        }
        return format_html(f"<span class='badge {colors[obj.download_status]}'>{obj.download_status}</span>")


def add_translations_into_json(modeladmin, request, queryset):
    versions = queryset.all()
    for s_version in versions:
        s_version.json = add_syllabus_translations(s_version.json)
        s_version.save()


@admin.register(SyllabusVersionProxy)
class SyllabusVersionAdmin(admin.ModelAdmin):
    list_display = ['syllabus', 'version', 'status']
    search_fields = ('syllabus__slug', 'syllabus__name')
    # raw_id_fields = ['assets']
    list_filter = ['syllabus']
    actions = [add_translations_into_json]
