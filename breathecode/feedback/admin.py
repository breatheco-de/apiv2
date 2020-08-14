from django.contrib import admin
from django.contrib.auth.models import User
from .models import Answer

# Register your models here.
@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ('user', 'score', 'entity_type', 'entity', 'comment', 'created_at')
    def entity(self, object):
        return f"{object.entity_slug} (id:{str(object.entity_id)})"