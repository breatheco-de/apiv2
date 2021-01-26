import os, requests, sys, pytz
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError

from ...actions import delete_tokens
from ...models import Capability, Role

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
            { "slug": "read_events", "description": "List and retrieve event information" },
            { "slug": "crud_events", "description": "Create, update or delete event information" },
            { "slug": "read_cohorts", "description": "List all the cohorts or a single cohort information" },
            { "slug": "crud_cohorts", "description": "Create, update or delete cohort info" },
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
            { "slug": "teacher", "name": "Teacher", "caps": ["crud_assignment", "read_syllabus","read_assignment"] },
            { "slug": "assistant", "name": "Teacher Assistant", "caps": ["read_assigment, crud_assignment"] },
            { "slug": "career_support", "name": "Career Support Specialist", "caps": ["read_certificate", "crud_certificate"] },
            { "slug": "growth_manager", "name": "Growth Manager", "caps": ["read_events", "crud_events"] },
            
        ]

        teacher = next(item for item in roles if item["slug"] == "teacher")
        #                                                                               inherit all the caps from the teacher role
        roles.append({ "slug": "academy_coordinator", "name": "Mentor in residence", "caps": teacher["caps"] + ["crud_syllabus"] })

        # TODO: Create country_manager role, that inheritls from all othe roles minus admin
        # inhered_caps = next(item for item in roles if item["slug"] in ["teacher", "assistant", "student", "career_support"])
        # roles.append({ "slug": "country_manager", "name": "Country Manage", "caps": inhered_caps["caps"] + ["crud_cohort", "read_cohort"] })

        for r in roles:
            _r = Role.objects.filter(slug=r["slug"]).first()
            if _r is None:
                _r = Role(slug=r["slug"], name=r["name"])
                _r.save()

            _r.capabilities.clear()
            for c in r["caps"]:
                _r.capabilities.add(c)
