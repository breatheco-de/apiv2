import base64
from django.contrib import admin
from urllib.parse import urlparse
from django.contrib.auth.admin import UserAdmin
from .actions import delete_tokens
from django.utils.html import format_html
from .models import CredentialsGithub, Token, UserProxy, Profile, CredentialsSlack, ProfileAcademy
from .actions import reset_password
# Register your models here.

def clean_all_tokens(modeladmin, request, queryset):
    user_ids = queryset.values_list('id', flat=True)
    count = delete_tokens(users=user_ids, status='all')
clean_all_tokens.short_description = "Delete all tokens"

def clean_expired_tokens(modeladmin, request, queryset):
    user_ids = queryset.values_list('id', flat=True)
    count = delete_tokens(users=user_ids, status='expired')
clean_expired_tokens.short_description = "Delete EXPIRED tokens"

def send_reset_password(modeladmin, request, queryset):
    reset_password(users=queryset)
send_reset_password.short_description = "Send reset password link"

@admin.register(CredentialsGithub)
class CredentialsGithubAdmin(admin.ModelAdmin):
    list_display = ('github_id', 'user_id', 'email', 'token')

@admin.register(CredentialsSlack)
class CredentialsSlackAdmin(admin.ModelAdmin):
    list_display = ('user','app_id', 'bot_user_id', 'team_id', 'team_name')

@admin.register(Token)
class TokenAdmin(admin.ModelAdmin):
    list_display = ('key', 'token_type', 'expires_at', 'user')
    raw_id_fields = ["user"]
    def get_readonly_fields(self, request, obj=None):
        return ['key']

@admin.register(UserProxy)
class UserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff')
    actions = [clean_all_tokens, clean_expired_tokens, send_reset_password]
    
@admin.register(ProfileAcademy)
class ProfileAcademyAdmin(admin.ModelAdmin):
    list_display = ('user', 'academy', 'created_at', 'slack')
    raw_id_fields = ["user"]
    
    def get_queryset(self, request):
        
        self.slack_callback = f"/v1/auth/slack/callback"
        self.slack_callback = str(base64.urlsafe_b64encode(self.slack_callback.encode("utf-8")), "utf-8")
        return super(ProfileAcademyAdmin, self).get_queryset(request)
    
    def slack(self,obj):
        return format_html(f"<a rel='noopener noreferrer' target='_blank' href='/v1/auth/slack/?a={obj.academy.id}&user={obj.user.id}&url={self.slack_callback}'>connect slack</a>")


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'avatar_url')
    # actions = [clean_all_tokens, clean_expired_tokens, send_reset_password]