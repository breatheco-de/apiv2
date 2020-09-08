from django.contrib import admin
from django.contrib.auth.models import User
from .models import Device

# Register your models here.
@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ('user', 'registration_id')