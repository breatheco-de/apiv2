from django.core.management.base import BaseCommand
from breathecode.payments.models import PaymentContact, Academy
from collections import defaultdict


class Command(BaseCommand):
    help = "Remove repeated PaymentContacts (keep oldest, assign academy 47 to the oldest one)"

    def handle(self, *args, **options):
        try:
            contact_academy = Academy.objects.get(id=47)
        except Academy.DoesNotExist:
            self.stdout.write(self.style.ERROR("Academy with id 47 does not exist."))
            return

        contacts_by_email = defaultdict(list)
        for contact in PaymentContact.objects.all():
            contacts_by_email[contact.user.email].append(contact)

        deleted = []

        for email, contacts in contacts_by_email.items():
            if len(contacts) > 1:
                contacts.sort(key=lambda c: getattr(c, "created_at", c.id))
                oldest = contacts[0]
                if oldest.academy_id != 47:
                    oldest.academy = contact_academy
                    oldest.save()
                for contact in contacts[1:]:
                    deleted.append(f"{email} (ID: {contact.id})")
                    contact.delete()

        if deleted:
            msg = "Deleted repeated contacts:\n" + "\n".join(deleted)
            self.stdout.write(self.style.SUCCESS(msg))
        else:
            self.stdout.write(self.style.WARNING("No repeated contacts found to delete."))
