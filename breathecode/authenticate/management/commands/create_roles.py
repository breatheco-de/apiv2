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
            { "slug": "student", "name": "Student", "caps": ["crud_assignment", "read_syllabus", "read_assignment"] },
            { "slug": "assistant", "name": "Teacher Assistant", "caps": ["read_assigment, crud_assignment"] },
            { "slug": "career_support", "name": "Career Support Specialist", "caps": ["read_certificate", "crud_certificate"] },
            { "slug": "admissions_developer", "name": "Admissions Developer", "caps": ["read_lead", "read_event", "read_eventcheckin"] },
            { "slug": "growth_manager", "name": "Growth Manager", "caps": ["read_event", "crud_event", "read_eventcheckin", "read_nps_answers", "read_lead"] },
        ]

        roles.append({ "slug": "teacher", "name": "Teacher", "caps": extend(roles, ["assistant"]) })
        roles.append({ "slug": "academy_coordinator", "name": "Mentor in residence", "caps": extend(roles, ["teacher"]) + ["crud_syllabus"] })
        roles.append({ "slug": "country_manager", "name": "Country Manager", "caps": extend(roles,["academy_coordinator", "student", "career_support", "growth_manager", "admissions_developer"]) + ["crud_cohort", "read_cohort"] })

        for r in roles:
            _r = Role.objects.filter(slug=r["slug"]).first()
            if _r is None:
                _r = Role(slug=r["slug"], name=r["name"])
                _r.save()

            _r.capabilities.clear()
            for c in r["caps"]:
                _r.capabilities.add(c)
