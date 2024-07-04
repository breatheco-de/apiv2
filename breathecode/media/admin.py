from django.contrib import admin
from .models import Media, MediaResolution, Category
from django.utils.html import format_html


@admin.register(Media)
class MediaAdmin(admin.ModelAdmin):
    search_fields = ["slug", "name"]
    list_display = ("slug", "name", "mime", "hits", "academy", "open_url")
    list_filter = ["categories", "mime", "academy"]

    def open_url(self, obj):
        return format_html(f"<a target='blank' href='/v1/media/file/{obj.slug}'>/v1/media/file/{obj.slug}</span>")


@admin.register(Category)
class MediaCategoryAdmin(admin.ModelAdmin):
    list_display = ("slug", "name", "created_at")


@admin.register(MediaResolution)
class MediaResolutionAdmin(admin.ModelAdmin):
    list_display = ("hash", "width", "height", "hits")
    list_filter = ["hash", "width", "height", "hits"]
