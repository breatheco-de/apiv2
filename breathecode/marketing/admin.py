from django.contrib import admin
from .models import FormEntry, Tag
# Register your models here.

@admin.register(FormEntry)
class FormEntryAdmin(admin.ModelAdmin):
    search_fields = ['email', 'first_name', 'last_name', 'phone']
    list_display = ('storage_status', 'first_name', 'last_name', 'email', 'phone', 'utm_url', 'created_at')
    list_filter = ['storage_status']
    # fields = ['first_name', 'last_name', ('date_of_birth', 'date_of_death')]

def mark_tag_as_strong(modeladmin, request, queryset):
    queryset.update(tag_type='STRONG')
mark_tag_as_strong.short_description = "Mark tags as STRONG"
def mark_tag_as_soft(modeladmin, request, queryset):
    queryset.update(tag_type='SOFT')
mark_tag_as_soft.short_description = "Mark tags as SOFT"
def mark_tag_as_discovery(modeladmin, request, queryset):
    queryset.update(tag_type='DISCOVERY')
mark_tag_as_discovery.short_description = "Mark tags as DISCOVERY"
def mark_tag_as_other(modeladmin, request, queryset):
    queryset.update(tag_type='OTHER')
mark_tag_as_other.short_description = "Mark tags as OTHER"

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    search_fields = ['slug']
    list_display = ('id', 'slug', 'tag_type', 'acp_id', 'subscribers')
    list_filter = ['tag_type']
    actions = [mark_tag_as_strong, mark_tag_as_soft, mark_tag_as_discovery, mark_tag_as_other]
