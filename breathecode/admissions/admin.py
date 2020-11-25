import pytz
from django.contrib import admin
from django import forms 
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from .models import Academy, Certificate, Cohort, CohortUser, Country, City, UserAdmissions
from breathecode.assignments.actions import sync_student_tasks
# Register your models here.
admin.site.site_header = "BreatheCode"
admin.site.index_title = "Administration Portal"
admin.site.site_title = "Administration Portal"

timezones = [(x, x) for x in pytz.common_timezones]

@admin.register(UserAdmissions)
class UserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff')

class AcademyForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
       super(AcademyForm, self).__init__(*args, **kwargs)
       if self.instance.id:
           self.fields['timezone'] = forms.ChoiceField(choices=timezones)
@admin.register(Academy)
class AcademyAdmin(admin.ModelAdmin):
    form = AcademyForm
    list_display = ('slug', 'name', 'city')

@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ('code', 'name')

@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ('name', 'country')


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ('slug', 'name', 'duration_in_hours')


@admin.register(CohortUser)
class CohortUserAdmin(admin.ModelAdmin):
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'cohort__slug', 'cohort__name', 'cohort__slug']
    list_display = ('get_student', 'cohort', 'role', 'educational_status', 'finantial_status', 'created_at')
    list_filter = ['role', 'educational_status','finantial_status']
    raw_id_fields = ["user", "cohort"]

    def get_student(self, obj):
        return obj.user.first_name + " " + obj.user.last_name + "(" + obj.user.email + ")"

def sync_tasks(modeladmin, request, queryset):
    cohort_ids = queryset.values_list('id', flat=True)
    cohort_user = CohortUser.objects.filter(cohort__id__in=[cohort_ids])
    for cu in cohort_user:
        sync_student_tasks(cu.user)

sync_tasks.short_description = "Sync Tasks"

class CohortForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
       super(CohortForm, self).__init__(*args, **kwargs)
       if self.instance.id:
           self.fields['timezone'] = forms.ChoiceField(choices=timezones)

@admin.register(Cohort)
class CohortAdmin(admin.ModelAdmin):
    form = CohortForm
    search_fields = ['slug', 'name', 'academy__city__name', 'certificate__slug']
    list_display = ('id', 'slug', 'stage', 'name', 'kickoff_date', 'certificate_name')
    list_filter = ['stage', 'academy__slug','certificate__slug']
    actions = [sync_tasks]

    def academy_name(self, obj):
        return obj.academy.name

    def certificate_name(self, obj):
        return obj.certificate.name





