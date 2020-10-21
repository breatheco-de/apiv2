from django.contrib import admin
from django.contrib.auth.models import User
from .models import Endpoint, Application
from django.utils.html import format_html
from .actions import get_website_text, run_app_diagnostig
from breathecode.notify.actions import send_email_message

def test_app(modeladmin, request, queryset):
    appications = queryset.all()
    for app in appications:
        result = run_app_diagnostig(app)
test_app.short_description = "Run Applications Diagnostic"

# Register your models here.
@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('title', 'status')
    actions=[test_app]

def test_endpoint(modeladmin, request, queryset):
    endpoints = queryset.all()
    for end in endpoints:
        get_website_text(end)
test_endpoint.short_description = "Test Endpoint"

# Register your models here.
@admin.register(Endpoint)
class EndpointAdmin(admin.ModelAdmin):
    list_display = ('url', 'current_status', 'test_pattern', 'status_code', 'last_check')
    actions=[test_endpoint]
    
    def current_status(self,obj):
        colors = {
            "OPERATIONAL": "bg-success",
            "CRITICAL": "bg-error",
            "MINOR": "bg-warning",
        }
        return format_html(f"<span class='badge {colors[obj.status]}'>{obj.status}</a>")