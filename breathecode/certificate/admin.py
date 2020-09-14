import requests, base64, re, json
from django.contrib import admin
from django.contrib import messages
from django.utils.html import format_html
from .models import Badge, Specialty, UserSpecialty

@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ('slug', 'name')

@admin.register(Specialty)
class SpecialtyAdmin(admin.ModelAdmin):
    list_display = ('slug', 'name')

@admin.register(UserSpecialty)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ('user', 'specialty', 'expires_at', 'academy', 'cohort', 'pdf', 'preview')
    list_filter = ['specialty', 'academy__slug','cohort__slug']
    
    def pdf(self,obj):
        return format_html(f"<a rel='noopener noreferrer' target='_blank' href='https://certificate.breatheco.de/pdf/{obj.token}'>pdf</a>")
    def preview(self,obj):
        return format_html("<a rel='noopener noreferrer' target='_blank' href='{url}'>preview</a>", url=obj.preview_url)

    def get_readonly_fields(self, request, obj=None):
        return ['token', 'expires_at']