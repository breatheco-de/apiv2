from django.contrib import admin
from .actions import delete_tokens
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from .models import CredentialsGithub, Token
# Register your models here.

def clean_all_tokens(modeladmin, request, queryset):
    user_ids = queryset.values_list('id', flat=True)
    count = delete_tokens(users=user_ids, status='all')
clean_all_tokens.short_description = "Delete all tokens"

def clean_expired_tokens(modeladmin, request, queryset):
    user_ids = queryset.values_list('id', flat=True)
    count = delete_tokens(users=user_ids, status='expired')
clean_expired_tokens.short_description = "Delete EXPIRED tokens"

admin.site.unregister(User)
@admin.register(User)
class UserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff')
    actions = [clean_all_tokens, clean_expired_tokens]

@admin.register(CredentialsGithub)
class CredentialsGithubAdmin(admin.ModelAdmin):
    list_display = ('github_id', 'user_id', 'email', 'token')

@admin.register(Token)
class TokenAdmin(admin.ModelAdmin):
    list_display = ('key', 'token_type', 'expires_at', 'user')
    def get_readonly_fields(self, request, obj=None):
        return ['key']