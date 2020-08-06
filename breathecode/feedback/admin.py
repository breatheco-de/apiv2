from django.contrib import admin
from django.contrib.auth.models import User
from .models import Answer

# Register your models here.
@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ('score', 'user', 'comment')