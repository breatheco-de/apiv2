from django.contrib import admin
from django.contrib.auth.models import User
from .models import Event, Venue, EventType, EventCheckin

# Register your models here.
@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('slug', 'title', 'url')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "author":
            kwargs["queryset"] = User.objects.filter(is_staff=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

# Register your models here.
@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ('title', 'city', 'street_address')

# Register your models here.
@admin.register(EventType)
class EventTypeAdmin(admin.ModelAdmin):
    list_display = ('slug', 'name')

# Register your models here.
@admin.register(EventCheckin)
class EventCheckinAdmin(admin.ModelAdmin):
    list_display = ('event', 'attendee', 'created_at')