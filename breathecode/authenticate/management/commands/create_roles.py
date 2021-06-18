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

        # Here is a list of all the current capabilities in the system
        caps = [
            { "slug": "leer_mi_perfil", "description": "Read your academy information" },
            { "slug": "read_my_academy", "description": "Read your academy information" },
            { "slug": "crud_my_academy", "description": "Read, or update your academy information (very high level, almost the academy admin)" },
            { "slug": "crud_member", "description": "Create, update or delete academy members (very high level, almost the academy admin)" },
            { "slug": "read_member", "description": "Read academy staff member information" },
            { "slug": "crud_student", "description": "Create, update or delete students" },
            { "slug": "read_student", "description": "Read student information" },
            { "slug": "read_invite", "description": "Read invites from users" },
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
            { "slug": "read_survey", "description": "List all the nps answers" },
            { "slug": "crud_survey", "description": "Create, update or delete surveys" },
            { "slug": "read_nps_answers", "description": "List all the nps answers" },
            { "slug": "read_lead", "description": "List all the leads" },
            { "slug": "crud_lead", "description": "Create, update or delete academy leads" },
            { "slug": "read_media", "description": "List all the medias" },
            { "slug": "crud_media", "description": "Create, update or delete academy medias" },
            { "slug": "read_media_resolution", "description": "List all the medias resolutions" },
            { "slug": "crud_media_resolution", "description": "Create, update or delete academy media resolutions" },
            { "slug": "read_cohort_activity", "description": "Read low level activity in a cohort (attendancy, etc.)" },
            { "slug": "generate_academy_token", "description": "Create a new token only to be used by the academy" },
            { "slug": "get_academy_token", "description": "Read the academy token" },
            { "slug": "send_reset_password", "description": "Generate a temporal token and resend forgot password link" },
        ]

        for c in caps:
            _cap = Capability.objects.filter(slug=c["slug"]).first()
            if _cap is None:
                _cap = Capability(**c)
                _cap.save()
            else:
                _cap.description = c["description"]
                _cap.save()

        # These are the MAIN roles, they cannot be deleted by anyone at the academy.
        roles = [
            { "slug": "admin", "name": "Admin", "caps": [c["slug"] for c in caps] },
            { "slug": "academy_token", "name": "Academy Token", "caps": ["read_member", "read_syllabus", "read_student", "read_cohort", "read_media", "read_my_academy", "read_invite", "read_lead", "crud_lead"] },
            { "slug": "staff", "name": "Staff (Base)", "caps": ["read_member", "read_syllabus", "read_student", "read_cohort", "read_media", "read_my_academy", "read_invite", "get_academy_token" ] },
            { "slug": "student", "name": "Student", "caps": ["crud_assignment", "read_syllabus", "read_assignment", "read_cohort", "read_my_academy"] },
        ]

        # These are additional roles that extend from the base roles above, 
        # you can exend from more than one role but also add additional capabilitis at the end
        roles.append({ "slug": "assistant", "name": "Teacher Assistant", "caps": extend(roles, ["staff"]) + ["read_assigment", "crud_assignment", "read_cohort_activity", "read_nps_answers"] })
        roles.append({ "slug": "career_support", "name": "Career Support Specialist", "caps": extend(roles, ["staff"]) + ["read_certificate", "crud_certificate"] })
        roles.append({ "slug": "admissions_developer", "name": "Admissions Developer", "caps": extend(roles, ["staff"]) + ["crud_lead","crud_student","crud_cohort", "read_cohort","read_lead", "read_event", "read_eventcheckin"] })
        roles.append({ "slug": "syllabus_coordinator", "name": "Syllabus Coordinator", "caps": extend(roles, ["staff"]) + ["crud_syllabus", "crud_media"] })
        roles.append({ "slug": "culture_and_recruitment", "name": "Culture and Recruitment", "caps": extend(roles, ["staff"]) + ["crud_member"] })
        roles.append({ "slug": "community_manager", "name": "Manage Syllabus, Exercises and all academy content", "caps": extend(roles, ["staff"]) + ["crud_lead","read_event", "crud_event", "read_eventcheckin", "read_nps_answers", "read_lead", "read_cohort", "crud_media"] })
        roles.append({ "slug": "growth_manager", "name": "Growth Manager", "caps": extend(roles, ["staff", "community_manager"]) + ["crud_media"] })
        roles.append({ "slug": "homework_reviewer", "name": "Homework Reviewer", "caps": extend(roles, ["assistant"]) })
        roles.append({ "slug": "teacher", "name": "Teacher", "caps": extend(roles, ["assistant"]) })
        roles.append({ "slug": "academy_coordinator", "name": "Mentor in residence", "caps": extend(roles, ["teacher"]) + ["crud_syllabus", "crud_cohort", "crud_student", "crud_survey"] })
        roles.append({ "slug": "country_manager", "name": "Country Manager", "caps": extend(roles,["academy_coordinator", "student", "career_support", "growth_manager", "admissions_developer", "syllabus_coordinator"]) + ["crud_member", "crud_my_academy", "generate_academy_token", "send_reset_password"] })

        for r in roles:
            _r = Role.objects.filter(slug=r["slug"]).first()
            if _r is None:
                _r = Role(slug=r["slug"], name=r["name"])
                _r.save()

            _r.capabilities.clear()
            for c in r["caps"]:
                _r.capabilities.add(c)
