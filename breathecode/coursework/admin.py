import requests, base64, re, json
from django.contrib import admin
from django.contrib import messages
from .models import Course, Syllabus
from breathecode.authenticate.models import CredentialsGithub
# Register your models here.
@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('slug', 'name', 'duration_in_hours')

def sync_with_github(modeladmin, request, queryset):
    all_syllabus = queryset.all()
    credentials = CredentialsGithub.objects.filter(user=request.user).first()
    if credentials is None:
        messages.error(request,'No github credentials found')
    else:
        for syl in all_syllabus:
            #/repos/:owner/:repo/contents/:path
            regex = r"github\.com\/([0-9a-zA-Z-]+)\/([0-9a-zA-Z-]+)\/blob\/([0-9a-zA-Z-]+)\/([0-9a-zA-Z-\/\.]+)"
            matches = re.findall(regex, syl.github_url)
            print(matches, syl.github_url)
            if matches is None:
                messages.error(request,'Invalid github url, make sure it follows this format: https://github.com/:user/:repo/blob/:branch/:path')
                continue

            headers = { "Authorization": f"token {credentials.token}"}
            response = requests.get(f"https://api.github.com/repos/{matches[0][0]}/{matches[0][1]}/contents/{matches[0][3]}?ref="+matches[0][2],headers=headers)
            if response.status_code == 200:
                _file = response.json()
                syl.json = json.loads(base64.b64decode(_file["content"]).decode())
                syl.save()
            else:
                messages.error(request,f'Error {response.status_code} updating syllabus from github, make sure you have the correct access rights to the repository')

sync_with_github.short_description = "Sync from Github"

@admin.register(Syllabus)
class SyllabusAdmin(admin.ModelAdmin):
    list_display = ('slug', 'academy_owner', 'version')
    actions = [sync_with_github]