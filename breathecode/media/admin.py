from django.contrib import admin
from .models import Media, MediaResolution, Category


@admin.register(Media)
class MediaAdmin(admin.ModelAdmin):
    list_display = ('slug', 'name', 'mime', 'url', 'thumbnail', 'hash', 'hits',
                    'academy')
    list_filter = ['name', 'slug', 'hash', 'categories']


@admin.register(Category)
class MediaCategoryAdmin(admin.ModelAdmin):
    list_display = ('slug', 'name', 'created_at')


@admin.register(MediaResolution)
class MediaResolutionAdmin(admin.ModelAdmin):
    list_display = ('hash', 'width', 'height', 'hits')
    list_filter = ['hash', 'width', 'height', 'hits']
