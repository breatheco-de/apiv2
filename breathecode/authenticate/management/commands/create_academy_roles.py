from django.core.management.base import BaseCommand

from breathecode.authenticate.role_definitions import (
    CAPABILITIES,
    get_extended_roles,
    remove_duplicates,
)

from ...models import Capability, Role


class Command(BaseCommand):
    help = "Create default system capabilities"

    def handle(self, *args, **options):

        # Here is a list of all the current capabilities in the system
        caps = CAPABILITIES

        for c in caps:
            _cap = Capability.objects.filter(slug=c["slug"]).first()
            if _cap is None:
                _cap = Capability(**c)
                _cap.save()
            else:
                _cap.description = c["description"]
                _cap.save()

        # Get all roles (base + extended) from centralized role definitions
        roles = get_extended_roles()

        for r in roles:
            _r = Role.objects.filter(slug=r["slug"]).first()
            if _r is None:
                _r = Role(slug=r["slug"], name=r["name"])
                _r.save()

            _r.capabilities.clear()
            r["caps"] = remove_duplicates(r["caps"])
            for c in r["caps"]:
                _r.capabilities.add(c)
