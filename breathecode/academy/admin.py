from django.contrib import admin
from .models import Academy, Certificate, Cohort, CohortUser
# Register your models here.

@admin.register(Academy)
class AcademyAdmin(admin.ModelAdmin):
    list_display = ('slug', 'name', 'city')


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ('slug', 'name', 'duration_in_hours')


@admin.register(CohortUser)
class CohortUserAdmin(admin.ModelAdmin):
    list_display = ('get_student', 'cohort', 'role', 'educational_status', 'finantial_status', 'created_at')

    def get_student(self, obj):
        return obj.user.first_name + " " + obj.user.last_name + "(" + obj.user.email + ")"

@admin.register(Cohort)
class CohortAdmin(admin.ModelAdmin):
    list_display = ('id', 'slug', 'name', 'created_at')