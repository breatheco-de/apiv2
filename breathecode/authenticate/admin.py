from django.contrib import admin
from .models import CredentialsGithub
# Register your models here.

@admin.register(CredentialsGithub)
class CredentialsGithubAdmin(admin.ModelAdmin):
    list_display = ('github_id', 'user_id', 'email', 'token')
    # fields = ['first_name', 'last_name', ('date_of_birth', 'date_of_death')]