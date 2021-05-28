from django.contrib import admin
from .models import Media, MediaResolution


@admin.register(Media)
class AcademyCertificateAdmin(admin.ModelAdmin):
    list_display = ('slug', 'name', 'mime', 'url', 'thumbnail', 'hash', 'hits',
        'academy')
    list_filter = ['name', 'slug', 'hash']


@admin.register(MediaResolution)
class AcademyCertificateAdmin(admin.ModelAdmin):
    list_display = ('hash', 'width', 'height', 'hits')
    list_filter = ['hash', 'width', 'height', 'hits']
