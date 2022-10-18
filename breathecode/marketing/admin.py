import logging, secrets
from django.contrib import admin, messages
from django import forms
from .models import (FormEntry, Tag, Automation, ShortLink, ActiveCampaignAcademy, ActiveCampaignWebhook,
                     AcademyAlias, Downloadable, LeadGenerationApp, UTMField, AcademyProxy)
from .actions import (register_new_lead, save_get_geolocal, get_facebook_lead_info, test_ac_connection,
                      sync_tags, sync_automations, acp_ids, delete_tag)
from breathecode.services.activecampaign import ActiveCampaign
from django.utils import timezone
from django.utils.html import format_html
from django.contrib.admin import SimpleListFilter
from breathecode.utils import AdminExportCsvMixin
from breathecode.utils.admin import change_field
from breathecode.utils.validation_exception import ValidationException
# Register your models here.

logger = logging.getLogger(__name__)


def test_ac(modeladmin, request, queryset):
    entries = queryset.all()
    try:
        for entry in entries:
            test_ac_connection(entry)
        messages.success(request, message='Connection was a success')
    except Exception as e:
        logger.fatal(str(e))
        messages.error(request, message=str(e))


test_ac.short_description = '♼ Test connection to Active Campaign'


def sync_ac_tags(modeladmin, request, queryset):
    entries = queryset.all()
    try:
        for entry in entries:
            sync_tags(entry)
        messages.success(request, message='Tags imported successfully')
    except Exception as e:
        logger.fatal(str(e))
        messages.error(request, message=str(e))


sync_ac_tags.short_description = '♼ Sync AC Tags'


def sync_ac_automations(modeladmin, request, queryset):
    entries = queryset.all()
    try:
        for entry in entries:
            sync_automations(entry)
        messages.success(request, message='Automations imported successfully')
    except Exception as e:
        logger.fatal(str(e))
        messages.error(request, message=str(e))


sync_ac_automations.short_description = '♼ Sync AC Automations'


class CustomForm(forms.ModelForm):

    class Meta:
        model = ActiveCampaignAcademy
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(CustomForm, self).__init__(*args, **kwargs)
        self.fields['event_attendancy_automation'].queryset = Automation.objects.filter(
            ac_academy=self.instance.id)  # or something else


@admin.register(ActiveCampaignAcademy)
class ACAcademyAdmin(admin.ModelAdmin, AdminExportCsvMixin):
    form = CustomForm
    search_fields = ['academy__name', 'academy__slug']
    list_display = ('id', 'academy', 'ac_url', 'sync_status', 'last_interaction_at', 'sync_message')
    list_filter = ['academy__slug', 'sync_status']
    actions = [test_ac, sync_ac_tags, sync_ac_automations]


@admin.register(AcademyAlias)
class AcademyAliasAdmin(admin.ModelAdmin):
    search_fields = ['slug', 'active_campaign_slug', 'academy__slug', 'academy__title']
    list_display = ('slug', 'active_campaign_slug', 'academy')
    list_filter = ['academy__slug']


def generate_original_alias(modeladmin, request, queryset):
    academies = queryset.all()
    for a in academies:
        slug = a.active_campaign_slug
        if slug is None:
            slug = a.slug

        if AcademyAlias.objects.filter(slug=a.slug).first() is None:
            AcademyAlias.objects.create(slug=a.slug, active_campaign_slug=slug, academy=a)
            messages.add_message(request, messages.INFO, f'Alias {a.slug} successfully created')
        else:
            messages.add_message(request, messages.ERROR, f'Alias {a.slug} already exists')


@admin.register(AcademyProxy)
class AcademyAdmin(admin.ModelAdmin):
    list_display = ('slug', 'name')
    actions = [generate_original_alias]


def send_to_active_campaign(modeladmin, request, queryset):
    entries = queryset.all()
    total = {'error': 0, 'persisted': 0}
    entry = None
    try:
        for entry in entries:
            entry = register_new_lead(entry.toFormData())
            if entry.storage_status == 'PERSISTED':
                total['persisted'] += 1
            else:
                total['error'] += 1

    except Exception as e:
        total['error'] += 1
        entry.storage_status = 'ERROR'
        entry.storage_status_text = str(e)
        entry.save()

    messages.add_message(
        request, messages.SUCCESS,
        f"Persisted leads: {total['persisted']}. Not persisted: {total['error']}. You can check each lead storage_status_text for details."
    )


def fetch_more_facebook_info(modeladmin, request, queryset):
    entries = queryset.all()
    for entry in entries:
        get_facebook_lead_info(entry.id)


fetch_more_facebook_info.short_description = '♺ Download more info from facebook'


def get_geoinfo(modeladmin, request, queryset):
    entries = queryset.all()
    for entry in entries:

        form_enty = {
            'latitude': entry.latitude,
            'longitude': entry.longitude,
        }
        save_get_geolocal(entry, form_enty)


get_geoinfo.short_description = '🌐 Get GEO info'


class PPCFilter(SimpleListFilter):
    title = 'Source'  # or use _('country') for translated title
    parameter_name = 'source'

    def lookups(self, request, model_admin):
        mediums = ['From PPC', 'Course Report']
        return [(m, m) for m in mediums]

    def queryset(self, request, queryset):
        if self.value() == 'From PPC':
            return queryset.filter(gclid__isnull=False)
        if self.value() == 'Course Report':
            return queryset.filter(utm_medium='coursereportschoolpage')


@admin.register(FormEntry)
class FormEntryAdmin(admin.ModelAdmin, AdminExportCsvMixin):
    search_fields = ['email', 'first_name', 'last_name', 'phone', 'utm_campaign']
    list_display = ('id', '_storage_status', 'created_at', 'first_name', 'last_name', 'email', 'location',
                    'course', 'academy', 'country', 'city', 'utm_medium', 'utm_url', 'gclid', 'tags')
    list_filter = [
        'storage_status', 'location', 'course', 'deal_status', PPCFilter, 'lead_generation_app',
        'tag_objects__tag_type', 'automation_objects__slug', 'utm_medium', 'utm_campaign', 'utm_source'
    ]
    actions = [send_to_active_campaign, get_geoinfo, fetch_more_facebook_info, 'async_export_as_csv']

    def _storage_status(self, obj):
        colors = {
            'PUBLISHED': 'bg-success',
            'OK': 'bg-success',
            'ERROR': 'bg-error',
            'WARNING': 'bg-warning',
            'DUPLICATED': '',
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

        return format_html(
            f"<p class='{from_status(obj.storage_status)}'>{obj.storage_status}</p><small>{obj.storage_status_text}</small>"
        )


def add_dispute(modeladmin, request, queryset):
    queryset.update(disputed_at=timezone.now())


def remove_dispute(modeladmin, request, queryset):
    queryset.update(disputed_at=None)


def delete_from_everywhere(modeladmin, request, queryset):

    for t in queryset:
        slug = t.slug
        try:
            if delete_tag(t) == True:
                messages.add_message(request, messages.INFO, f'Tag {slug} successully deleted')
            else:
                messages.add_message(request, messages.ERROR, f'Error deleding tag {slug}')
        except Exception as e:
            messages.add_message(request, messages.ERROR, f'Error deleding tag {slug}: {str(e)}')


def upload_to_active_campaign(modeladmin, request, queryset):

    for t in queryset:
        slug = t.slug
        try:
            ac_academy = t.ac_academy
            if ac_academy is None:
                raise ValidationException(f'Invalid ac_academy for this tag {t.slug}',
                                          code=400,
                                          slug='invalid-ac_academy')

            client = ActiveCampaign(ac_academy.ac_key, ac_academy.ac_url)
            data = client.create_tag(t.slug, description=t.description)
            t.acp_id = data['id']
            t.subscribers = 0
            t.save()
            messages.add_message(request, messages.INFO, f'Tag {t.slug} successully uploaded')
        except Exception as e:
            messages.add_message(request, messages.ERROR, f'Error uploading tag {slug}: {str(e)}')


def prepend_tech_on_name(modeladmin, request, queryset):

    for t in queryset:
        if t.slug[:5] == 'tech-':
            continue
        t.slug = 'tech-' + t.slug
        t.save()

    prepend_tech_on_name.short_description = 'Prepend "tech-" on slug'


class CustomTagModelForm(forms.ModelForm):

    class Meta:
        model = Tag
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(CustomTagModelForm, self).__init__(*args, **kwargs)
        if self.instance.ac_academy is not None:
            self.fields['automation'].queryset = Automation.objects.filter(
                ac_academy=self.instance.ac_academy.id)  # or something else


class TagTypeFilter(SimpleListFilter):
    title = 'tag_type'
    parameter_name = 'tag_type'

    def lookups(self, request, model_admin):
        tags = set([c.tag_type for c in Tag.objects.filter(tag_type__isnull=False)])
        return [(c, c) for c in tags] + [('NONE', 'No type')]

    def queryset(self, request, queryset):
        if self.value() == 'NONE':
            return queryset.filter(tag_type__isnull=True)
        if self.value():
            return queryset.filter(tag_type__exact=self.value())


class DisputedFilter(admin.SimpleListFilter):

    title = 'Disputed tag'

    parameter_name = 'is_disputed'

    def lookups(self, request, model_admin):

        return (
            ('yes', 'Yes'),
            ('no', 'No'),
        )

    def queryset(self, request, queryset):

        if self.value() == 'yes':
            return queryset.filter(disputed_at__isnull=False)

        if self.value() == 'no':
            return queryset.filter(disputed_at__isnull=True)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin, AdminExportCsvMixin):
    form = CustomTagModelForm
    search_fields = ['slug']
    list_display = ('id', 'slug', 'tag_type', 'disputed', 'ac_academy', 'acp_id', 'subscribers')
    list_filter = [DisputedFilter, TagTypeFilter, 'ac_academy__academy__slug']
    actions = [
        delete_from_everywhere, 'export_as_csv', upload_to_active_campaign, add_dispute, remove_dispute,
        prepend_tech_on_name
    ] + change_field(['STRONG', 'SOFT', 'DISCOVERY', 'COHORT', 'DOWNLOADABLE', 'EVENT', 'OTHER'],
                     name='tag_type')

    def disputed(self, obj):
        if obj.disputed_at is not None:
            return format_html(
                f"<div><span class='badge bg-error' style='font-size: 11px;'>Will delete</span><p style='margin:0; padding: 0; font-size: 9px;'>On {obj.disputed_at.strftime('%b %d, %y')}</p></div>"
            )
        else:
            return format_html(f"<span class='badge'></span>")


@admin.register(Automation)
class AutomationAdmin(admin.ModelAdmin, AdminExportCsvMixin):
    search_fields = ['slug', 'name']
    list_display = ('id', 'acp_id', 'slug', 'name', 'status', 'entered', 'exited')
    list_filter = ['status', 'ac_academy__academy__slug']
    actions = ['export_as_csv']


@admin.register(ShortLink)
class ShortLinkAdmin(admin.ModelAdmin, AdminExportCsvMixin):
    search_fields = ['slug', 'destination']
    list_display = ('id', 'slug', 'hits', 'current_status', 'active', 'lastclick_at', 'link')
    list_filter = ['destination_status', 'active']
    actions = ['export_as_csv']

    def current_status(self, obj):
        colors = {
            'ACTIVE': 'bg-success',
            'ERROR': 'bg-error',
            'NOT_FOUND': 'bg-warning',
        }

        return format_html(
            f"<span class='badge {colors[obj.destination_status]}'>{obj.destination_status}</span>")

    def link(self, obj):
        return format_html("<a rel='noopener noreferrer' target='_blank' href='{url}'>{short_link}</a>",
                           url=f'https://s.4geeks.co/s/{obj.slug}',
                           short_link=f'https://s.4geeks.co/s/{obj.slug}')


def run_hook(modeladmin, request, queryset):
    # stay this here for use the poor mocking system
    for hook in queryset.all():
        ac_academy = hook.ac_academy
        client = ActiveCampaign(ac_academy.ac_key, ac_academy.ac_url)
        client.execute_action(hook.id, acp_ids)


run_hook.short_description = 'Process Hook'


@admin.register(ActiveCampaignWebhook)
class ActiveCampaignWebhookAdmin(admin.ModelAdmin):
    list_display = ('id', 'webhook_type', 'current_status', 'run_at', 'initiated_by', 'created_at')
    list_filter = ['status', 'webhook_type']
    actions = [run_hook]

    def current_status(self, obj):
        colors = {
            'DONE': 'bg-success',
            'ERROR': 'bg-error',
            'PENDING': 'bg-warning',
        }
        return format_html(f"<span class='badge {colors[obj.status]}'>{obj.status}</span>")


@admin.register(Downloadable)
class DownloadableAdmin(admin.ModelAdmin):
    list_display = ('slug', 'name', 'academy', 'status', 'open_link')

    def open_link(self, obj):
        return format_html(f"<a href='{obj.destination_url}' target='parent'>open link</a>")

    def status(self, obj):
        colors = {
            'ACTIVE': 'bg-success',
            'NOT_FOUND': 'bg-error',
        }
        return format_html(
            f"<span class='badge {colors[obj.destination_status]}'>{obj.destination_status}</span>")


def reset_app_id(modeladmin, request, queryset):
    for app in queryset.all():
        app.app_id = secrets.token_urlsafe(16)
        app.save()


reset_app_id.short_description = 'Reset app id'


class LeadAppCustomForm(forms.ModelForm):

    class Meta:
        model = LeadGenerationApp
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(LeadAppCustomForm, self).__init__(*args, **kwargs)

        try:
            if 'default_automations' in self.fields:
                self.fields['default_automations'].queryset = Automation.objects.filter(
                    ac_academy__academy__id=self.instance.academy.id).exclude(slug='')  # or something else
            self.fields['default_tags'].queryset = Tag.objects.filter(
                ac_academy__academy__id=self.instance.academy.id)  # or something else
        except:
            self.fields['default_automations'].queryset = Automation.objects.none()
            self.fields['default_tags'].queryset = Tag.objects.none()


@admin.register(LeadGenerationApp)
class LeadGenerationAppAdmin(admin.ModelAdmin):
    form = LeadAppCustomForm
    list_display = ('slug', 'name', 'academy', 'status', 'last_call_at', 'app_id')
    readonly_fields = ('app_id', )
    actions = (reset_app_id, )

    def status(self, obj):
        colors = {
            'OK': 'bg-success',
            'ERROR': 'bg-error',
        }
        if obj.last_call_status is None:
            return format_html(f"<span class='badge'>Not yet called</span>")
        return format_html(
            f"<span class='badge {colors[obj.last_call_status]}'>{obj.last_call_status}</span>")


@admin.register(UTMField)
class UTMFieldAdmin(admin.ModelAdmin):
    list_display = ('slug', 'name', 'utm_type')
    list_filter = ['utm_type', 'academy__slug']
    actions = change_field(['SOURCE', 'MEDIUM', 'CAMPAIGN', 'CONTENT'], name='utm_type')
