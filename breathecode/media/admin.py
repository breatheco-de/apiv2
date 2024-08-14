from django.contrib import admin
from django.utils.html import format_html

from .models import Category, Chunk, File, Media, MediaResolution


@admin.register(Media)
class MediaAdmin(admin.ModelAdmin):
    search_fields = ["slug", "name"]
    list_display = ("slug", "name", "mime", "hits", "academy", "open_url")
    list_filter = ["categories", "mime", "academy"]

    def open_url(self, obj):
        return format_html(f"<a target='blank' href='/v1/media/file/{obj.slug}'>/v1/media/file/{obj.slug}</a>")


@admin.register(Category)
class MediaCategoryAdmin(admin.ModelAdmin):
    list_display = ("slug", "name", "created_at")


@admin.register(MediaResolution)
class MediaResolutionAdmin(admin.ModelAdmin):
    list_display = ("hash", "width", "height", "hits")
    list_filter = ["hash", "width", "height", "hits"]


@admin.register(Chunk)
class ChunkAdmin(admin.ModelAdmin):
    list_display = ("name", "mime", "user", "academy", "chunk_index", "total_chunks", "operation_type", "open_url")
    search_fields = ["name"]
    list_filter = ["operation_type", "mime", "academy"]

    def open_url(self, obj: Chunk) -> str:
        return format_html(
            f"<a target='blank' href='https://storage.googleapis.com/{obj.bucket}/{obj.file_name}'>{obj.bucket}/{obj.file_name}</a>"
        )


@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    list_display = ("name", "mime", "status", "user", "academy", "hash", "size", "operation_type", "open_url")
    search_fields = ["name", "hash"]
    list_filter = ["operation_type", "mime", "academy", "status"]

    def open_url(self, obj: File) -> str:
        if obj.status == File.Status.TRANSFERRED:
            return "File transferred"

        return format_html(
            f"<a target='blank' href='https://storage.googleapis.com/{obj.bucket}/{obj.file_name}'>{obj.bucket}/{obj.file_name}</a>"
        )
