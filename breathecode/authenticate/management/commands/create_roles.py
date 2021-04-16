import os, requests, sys, pytz
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError

from ...actions import delete_tokens
from ...models import Capability, Role

def extend(roles, slugs):
    caps_groups = [item["caps"] for item in roles if item["slug"] in slugs]
    inhered_caps = []
    for roles in caps_groups:
        inhered_caps = inhered_caps + roles
    return list(dict.fromkeys(inhered_caps))

class Command(BaseCommand):
    help = 'Create default system capabilities'

    def handle(self, *args, **options):

        caps = [
            { "slug": "crud_member", "description": "Create, update or delete academy members (very high level, almost the academy admin)" },
            { "slug": "read_member", "description": "Read academy staff member information" },
            { "slug": "crud_student", "description": "Create, update or delete students" },
            { "slug": "read_student", "description": "Read student information" },
            { "slug": "read_assignment", "description": "Read assigment information" },
            { "slug": "crud_assignment", "description": "Update assignments" },
            { "slug": "read_certificate", "description": "List and read all academy certificates" },
            { "slug": "crud_certificate", "description": "Create, update or delete student certificates" },
            { "slug": "read_syllabus", "description": "List and read syllabus information" },
            { "slug": "crud_syllabus", "description": "Create, update or delete syllabus versions" },
            { "slug": "read_event", "description": "List and retrieve event information" },
            { "slug": "crud_event", "description": "Create, update or delete event information" },
            { "slug": "read_cohort", "description": "List all the cohorts or a single cohort information" },
            { "slug": "crud_cohort", "description": "Create, update or delete cohort info" },
            { "slug": "read_eventcheckin", "description": "List and read all the event_checkins" },
            { "slug": "read_nps_answers", "description": "List all the nps answers" },
            { "slug": "read_lead", "description": "List all the leads" },
            { "slug": "crud_lead", "description": "Create, update or delete academy leads" },
            { "slug": "read_media", "description": "List all the medias" },
            { "slug": "crud_media", "description": "Create, update or delete academy medias" },
            { "slug": "read_cohort_activity", "description": "Read low level activity in a cohort (attendancy, etc.)" },
        ]

        for c in caps:
            _cap = Capability.objects.filter(slug=c["slug"]).first()
            if _cap is None:
                _cap = Capability(**c)
                _cap.save()
            else:
                _cap.description = c["description"]
                _cap.save()

        roles = [
            { "slug": "admin", "name": "Admin", "caps": [c["slug"] for c in caps] },
            { "slug": "staff", "name": "Staff (Base)", "caps": ["read_member", "read_syllabus", "read_student", "read_cohort"] },
            { "slug": "student", "name": "Student", "caps": ["crud_assignment", "read_syllabus", "read_assignment", "read_cohort"] },
        ]

        roles.append({ "slug": "assistant", "name": "Growth Manager", "caps": extend(roles, ["staff"]) + ["read_assigment", "crud_assignment", "read_cohort_activity"] })
        roles.append({ "slug": "career_support", "name": "Career Support Specialist", "caps": extend(roles, ["staff"]) + ["read_certificate", "crud_certificate"] })
        roles.append({ "slug": "admissions_developer", "name": "Admissions Developer", "caps": extend(roles, ["staff"]) + ["crud_lead","crud_student","crud_cohort", "read_cohort","read_lead", "read_event", "read_eventcheckin"] })
        roles.append({ "slug": "syllabus_coordinator", "name": "Manage Syllabus, Exercises and all academy content", "caps": extend(roles, ["staff"]) })
        roles.append({ "slug": "community_manager", "name": "Manage Syllabus, Exercises and all academy content", "caps": extend(roles, ["staff"]) + ["crud_lead","read_event", "crud_event", "read_eventcheckin", "read_nps_answers", "read_lead", "read_cohort"] })
        roles.append({ "slug": "growth_manager", "name": "Growth Manager", "caps": extend(roles, ["staff","community_manager"]) + ["read_media", "crud_media"] })
        roles.append({ "slug": "teacher", "name": "Teacher", "caps": extend(roles, ["assistant"]) })
        roles.append({ "slug": "academy_coordinator", "name": "Mentor in residence", "caps": extend(roles, ["teacher"]) + ["crud_syllabus", "crud_cohort", "crud_student"] })
        roles.append({ "slug": "country_manager", "name": "Country Manager", "caps": extend(roles,["academy_coordinator", "student", "career_support", "growth_manager", "admissions_developer", "syllabus_coordinator"]) + ["crud_member"] })

        for r in roles:
            _r = Role.objects.filter(slug=r["slug"]).first()
            if _r is None:
                _r = Role(slug=r["slug"], name=r["name"])
                _r.save()

            _r.capabilities.clear()
            for c in r["caps"]:
                _r.capabilities.add(c)
