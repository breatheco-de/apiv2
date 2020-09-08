import requests, base64, re, json
from django.contrib import admin
from django.contrib import messages
from .models import Badge, Specialty, UserSpecialty

@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ('slug', 'name')

@admin.register(Specialty)
class SpecialtyAdmin(admin.ModelAdmin):
    list_display = ('slug', 'name')

@admin.register(UserSpecialty)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ('user', 'specialty', 'token', 'expires_at')
    def get_readonly_fields(self, request, obj=None):
        return ['token', 'expires_at']