import base64, os, urllib.parse, logging, datetime
from django.contrib import admin
from django.utils import timezone
from urllib.parse import urlparse
from django.contrib.auth.admin import UserAdmin
from django.contrib import messages
from .actions import (delete_tokens, generate_academy_token, set_gitpod_user_expiration, reset_password,
                      sync_organization_members)
from django.utils.html import format_html
from .models import (CredentialsGithub, DeviceId, Token, UserProxy, Profile, CredentialsSlack, ProfileAcademy,
                     Role, CredentialsFacebook, Capability, UserInvite, CredentialsGoogle, AcademyProxy,
                     GitpodUser, GithubAcademyUser, AcademyAuthSettings)
from .tasks import async_set_gitpod_user_expiration
from breathecode.utils.admin import change_field
from breathecode.utils.datetime_interger import from_now
from django.db.models import QuerySet
from . import tasks

logger = logging.getLogger(__name__)


def clean_all_tokens(modeladmin, request, queryset):
    user_ids = queryset.values_list('id', flat=True)
    count = delete_tokens(users=user_ids, status='all')


clean_all_tokens.short_description = 'Delete all tokens'


def clean_expired_tokens(modeladmin, request, queryset):
    user_ids = queryset.values_list('id', flat=True)
    count = delete_tokens(users=user_ids, status='expired')


clean_expired_tokens.short_description = 'Delete EXPIRED tokens'


def send_reset_password(modeladmin, request, queryset):
    reset_password(users=queryset)


send_reset_password.short_description = 'Send reset password link'


@admin.register(CredentialsGithub)
class CredentialsGithubAdmin(admin.ModelAdmin):
    list_display = ('github_id', 'user_id', 'email', 'token')
    search_fields = ['user__first_name', 'user__last_name', 'user__email', 'email']
    raw_id_fields = ['user']


@admin.register(CredentialsGoogle)
class CredentialsGoogleAdmin(admin.ModelAdmin):
    list_display = ('user', 'token', 'expires_at')
    search_fields = [
        'user__first_name',
        'user__last_name',
        'user__email',
    ]
    raw_id_fields = ['user']


@admin.register(CredentialsSlack)
class CredentialsSlackAdmin(admin.ModelAdmin):
    list_display = ('user', 'app_id', 'bot_user_id', 'team_id', 'team_name')
    search_fields = ['user__first_name', 'user__last_name', 'user__email']
    raw_id_fields = ['user']


@admin.register(CredentialsFacebook)
class CredentialsFacebookAdmin(admin.ModelAdmin):
    list_display = ('facebook_id', 'user', 'email', 'academy', 'expires_at')


@admin.register(Token)
class TokenAdmin(admin.ModelAdmin):
    list_display = ('key', 'token_type', 'expires_at', 'user')
    search_fields = ('user__email', 'user__first_name', 'user__last_name')
    raw_id_fields = ['user']

    def get_readonly_fields(self, request, obj=None):
        return ['key']


def accept_selected_users_from_waiting_list(modeladmin, request, queryset: QuerySet[UserInvite]):
    queryset = queryset.exclude(process_status='DONE').order_by('id')
    for x in queryset:
        tasks.async_accept_user_from_waiting_list.delay(x.id)


def accept_all_users_from_waiting_list(modeladmin, request, queryset: QuerySet[UserInvite]):
    queryset = UserInvite.objects.all().exclude(process_status='DONE').order_by('id')
    for x in queryset:
        tasks.async_accept_user_from_waiting_list.delay(x.id)


@admin.register(UserInvite)
class UserInviteAdmin(admin.ModelAdmin):
    search_fields = ['email', 'first_name', 'last_name']
    list_filter = ['academy', 'role', 'status', 'process_status']
    list_display = ('email', 'first_name', 'last_name', 'status', 'academy', 'token', 'created_at',
                    'invite_url')
    actions = [accept_selected_users_from_waiting_list, accept_all_users_from_waiting_list]

    def invite_url(self, obj):
        params = {'callback': 'https://4geeks.com'}
        querystr = urllib.parse.urlencode(params)
        url = os.getenv('API_URL') + '/v1/auth/member/invite/' + str(obj.token) + '?' + querystr
        return format_html(f"<a rel='noopener noreferrer' target='_blank' href='{url}'>invite url</a>")


def clear_user_password(modeladmin, request, queryset):
    for u in queryset:
        u.set_unusable_password()
        u.save()


clear_user_password.short_description = 'Clear user password'


@admin.register(UserProxy)
class UserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'github_login')
    actions = [clean_all_tokens, clean_expired_tokens, send_reset_password, clear_user_password]

    def get_queryset(self, request):

        self.github_callback = f'https://4geeks.com'
        self.github_callback = str(base64.urlsafe_b64encode(self.github_callback.encode('utf-8')), 'utf-8')
        return super(UserAdmin, self).get_queryset(request)

    def github_login(self, obj):
        return format_html(
            f"<a rel='noopener noreferrer' target='_blank' href='/v1/auth/github/?user={obj.id}&url={self.github_callback}'>connect github</a>"
        )


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('slug', 'name')
    filter_horizontal = ('capabilities', )


@admin.register(Capability)
class CapabilityAdmin(admin.ModelAdmin):
    list_display = ('slug', 'description')


@admin.register(ProfileAcademy)
class ProfileAcademyAdmin(admin.ModelAdmin):
    list_display = ('user', 'stats', 'email', 'academy', 'role', 'created_at', 'slack', 'facebook')
    search_fields = ['user__first_name', 'user__last_name', 'user__email']
    list_filter = ['academy__slug', 'status', 'role__slug']
    actions = change_field(['ACTIVE', 'INVITED'], name='status')
    raw_id_fields = ['user']

    def get_queryset(self, request):

        self.slack_callback = f'https://4geeks.com'
        self.slack_callback = str(base64.urlsafe_b64encode(self.slack_callback.encode('utf-8')), 'utf-8')
        return super(ProfileAcademyAdmin, self).get_queryset(request)

    def stats(self, obj):

        colors = {
            'ACTIVE': 'bg-success',
            'INVITED': 'bg-error',
        }

        return format_html(
            f"<span class='badge {colors[obj.status]}'><a rel='noopener noreferrer' target='_blank' href='/v1/auth/academy/html/invite'>{obj.status}</a></span>"
        )

    def slack(self, obj):
        if obj.user is not None:
            return format_html(
                f"<a rel='noopener noreferrer' target='_blank' href='/v1/auth/slack/?a={obj.academy.id}&user={obj.user.id}&url={self.slack_callback}'>slack login</a>"
            )
        else:
            return 'Pending invite response'

    def facebook(self, obj):
        if obj.user is not None:
            return format_html(
                f"<a rel='noopener noreferrer' target='_blank' href='/v1/auth/facebook/?a={obj.academy.id}&user={obj.user.id}&url={self.slack_callback}'>facebook login</a>"
            )
        else:
            return 'Pending invite response'


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'github_username', 'avatar_url')
    search_fields = ['user__first_name', 'user__last_name', 'user__email']
    # actions = [clean_all_tokens, clean_expired_tokens, send_reset_password]


def generate_token(modeladmin, request, queryset):
    academies = queryset.all()
    for a in academies:
        token = generate_academy_token(a.id)


generate_token.short_description = 'Generate academy token'


def reset_token(modeladmin, request, queryset):
    academies = queryset.all()
    for a in academies:
        token = generate_academy_token(a.id, force=True)


reset_token.short_description = 'RESET academy token'


@admin.register(AcademyProxy)
class AcademyAdmin(admin.ModelAdmin):
    list_display = ('slug', 'name', 'token')
    actions = [generate_token, reset_token]

    def token(self, obj):
        return Token.objects.filter(user__username=obj.slug).first()


@admin.register(DeviceId)
class DeviceIdAdmin(admin.ModelAdmin):
    list_display = ('name', 'key')
    search_fields = ['name']


def async_recalculate_expiration(modeladmin, request, queryset):
    queryset.update(expires_at=None)
    gp_users = queryset.all()
    for gpu in gp_users:
        gpu = async_set_gitpod_user_expiration.delay(gpu.id)


def recalculate_expiration(modeladmin, request, queryset):
    queryset.update(expires_at=None)
    gp_users = queryset.all()
    for gpu in gp_users:
        gpu = set_gitpod_user_expiration(gpu.id)
        if gpu is None:
            messages.add_message(
                request, messages.ERROR,
                f'Error: Gitpod user {gpu.github_username} {gpu.assignee_id} could not be processed')
        else:
            messages.add_message(
                request, messages.INFO,
                f'Success: Gitpod user {gpu.github_username} {gpu.assignee_id} was successfully processed')


def async_recalculate_expiration(modeladmin, request, queryset):
    queryset.update(expires_at=None)
    gp_users = queryset.all()
    for gpu in gp_users:
        gpu = async_set_gitpod_user_expiration.delay(gpu.id)


def extend_expiration_2_weeks(modeladmin, request, queryset):
    gp_users = queryset.all()
    for gpu in gp_users:
        gpu.expires_at = gpu.expires_at + datetime.timedelta(days=17)
        gpu.delete_status = gpu.delete_status + '. The expiration date was extend for 2 weeks days'
        gpu.save()
        messages.add_message(request, messages.INFO, f'Success: Expiration was successfully extended')


def extend_expiration_4_months(modeladmin, request, queryset):
    gp_users = queryset.all()
    for gpu in gp_users:
        gpu.expires_at = gpu.expires_at + datetime.timedelta(days=120)
        gpu.delete_status = gpu.delete_status + '. The expiration date was extend for 4 months'
        gpu.save()
        messages.add_message(request, messages.INFO, f'Success: Expiration was successfully extended')


def mark_as_expired(modeladmin, request, queryset):
    gp_users = queryset.all()
    for gpu in gp_users:
        gpu.expires_at = timezone.now()
        gpu.delete_status = gpu.delete_status + '. The user was expired by force.'
        gpu.save()
        messages.add_message(request, messages.INFO, f'Success: Gitpod user was expired')


@admin.register(GitpodUser)
class GitpodUserAdmin(admin.ModelAdmin):
    list_display = ('github_username', 'expiration', 'user', 'assignee_id', 'expires_at')
    search_fields = ['github_username', 'user__email', 'user__first_name', 'user__last_name', 'assignee_id']
    actions = [
        async_recalculate_expiration, recalculate_expiration, extend_expiration_2_weeks,
        extend_expiration_4_months, mark_as_expired
    ]

    def expiration(self, obj):
        now = timezone.now()

        if obj.expires_at is None:
            return format_html(f"<span class='badge bg-warning'>NEVER</span>")
        elif now > obj.expires_at:
            return format_html(f"<span class='badge bg-error'>EXPIRED</span>")
        elif now > (obj.expires_at + datetime.timedelta(days=3)):
            return format_html(
                f"<span class='badge bg-warning'>In {from_now(obj.expires_at, include_days=True)}</span>")
        else:
            return format_html(
                f"<span class='badge bg-success'>In {from_now(obj.expires_at, include_days=True)}</span>")


def mark_as_deleted(modeladmin, request, queryset):
    queryset.all().update(storage_status='PENDING', storage_action='DELETE')


def mark_as_add(modeladmin, request, queryset):
    queryset.all().update(storage_status='PENDING', storage_action='ADD')


def mark_as_ignore(modeladmin, request, queryset):
    queryset.all().update(storage_status='SYNCHED', storage_action='IGNORE')


@admin.register(GithubAcademyUser)
class GithubAcademyUserAdmin(admin.ModelAdmin):
    list_display = ('academy', 'user', 'username', 'storage_status', 'storage_action')
    search_fields = ['username', 'user__email', 'user__first_name', 'user__last_name']
    actions = [mark_as_deleted, mark_as_add, mark_as_ignore]
    list_filter = ('academy', 'storage_status', 'storage_action')
    raw_id_fields = ['user']


def sync_github_members(modeladmin, request, queryset):
    settings = queryset.all()
    for s in settings:
        sync_organization_members(s.academy.id)


def activate_github_sync(modeladmin, request, queryset):
    queryset.update(github_is_sync=True)


def deactivate_github_sync(modeladmin, request, queryset):
    queryset.update(github_is_sync=False)


@admin.register(AcademyAuthSettings)
class AcademyAuthSettingsAdmin(admin.ModelAdmin):
    list_display = ('academy', 'github_is_sync', 'github_username', 'github_owner', 'authenticate')
    search_fields = ['academy__slug', 'academy__name', 'github__username', 'academy__id']
    actions = (sync_github_members, activate_github_sync, deactivate_github_sync)
    raw_id_fields = ['github_owner']

    def get_queryset(self, request):

        self.github_callback = f'https://4geeks.com'
        self.github_callback = str(base64.urlsafe_b64encode(self.github_callback.encode('utf-8')), 'utf-8')
        return super(AcademyAuthSettingsAdmin, self).get_queryset(request)

    def authenticate(self, obj):
        now = timezone.now()
        settings = AcademyAuthSettings.objects.get(id=obj.id)
        if settings.github_owner is None:
            return format_html(f'no owner')

        scopes = str(base64.urlsafe_b64encode(b'user repo admin:org'), 'utf-8')
        return format_html(
            f"<a href='/v1/auth/github?user={obj.github_owner.id}&url={self.github_callback}&scope={scopes}'>connect owner</a>"
        )
