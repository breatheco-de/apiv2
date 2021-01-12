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
            { "slug": "crud_assignment", "description": "Update assignments" },
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
            { "slug": "student", "name": "Student", "caps": ["crud_assignment"] },
        ]

        for r in roles:
            _r = Role.objects.filter(slug=r["slug"]).first()
            if _r is None:
                _r = Role(slug=r["slug"], name=r["name"])
                _r.save()

            _r.capabilities.clear()
            for c in r["caps"]:
                _r.capabilities.add(c)
