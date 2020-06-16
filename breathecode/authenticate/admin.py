from django.contrib import admin
from breathecode.authenticate.models import CredentialsGithub
# Register your models here.

@admin.register(CredentialsGithub)
class CredentialsGithubAdmin(admin.ModelAdmin):
    list_display = ('github_id', 'user', 'email', 'token')
    # fields = ['first_name', 'last_name', ('date_of_birth', 'date_of_death')]