from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .actions import delete_tokens
from .models import CredentialsGithub, Token, UserAutentication
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

@admin.register(Token)
class TokenAdmin(admin.ModelAdmin):
    list_display = ('key', 'token_type', 'expires_at', 'user')
    raw_id_fields = ["user"]
    def get_readonly_fields(self, request, obj=None):
        return ['key']

@admin.register(UserAutentication)
class UserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff')
    actions = [clean_all_tokens, clean_expired_tokens, send_reset_password]