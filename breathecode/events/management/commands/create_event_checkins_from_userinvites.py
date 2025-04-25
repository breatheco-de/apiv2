from django.core.management.base import BaseCommand
from breathecode.events.models import Event, EventCheckin
from breathecode.authenticate.models import UserInvite, User
from django.db import transaction
from django.contrib.auth.models import User

EVENT_SLUGS = [
    "join-the-vibe-coding-community-now",
    "part-1-vibe-coding-with-ai-coding-essentials",
    "parte-1-codificando-con-ia-la-base-y-fundamentos",
    "part-2-vibe-coding-with-ai-mastering-ai-fundamentals",
    "parte-2-vibe-coding-con-ia-fundamentos-para-la-generacion",
    "part-3-vibe-coding-with-ai-launch-a-product-fast",
    "parte-3-vibe-coding-con-ia-lanza-un-producto-rapidament",
    "part-4-vibe-coding-with-ai-iterate-and-maintain-your-product",
    "parte-4-maestria-vibe-coding-itera-y-manten-tu-proyecto",
]

class Command(BaseCommand):
    help = 'Create EventCheckin for users from UserInvite for specific event slugs.'

    def handle(self, *args, **options):
        created_count = 0
        for slug in EVENT_SLUGS:
            event = Event.objects.filter(slug=slug).first()
            if not event:
                print(f'Event with slug "{slug}" not found.')
                continue

            invites = UserInvite.objects.filter(event_slug=slug)
            if not invites.exists():
                print(f'No UserInvites found for event_slug "{slug}".')
                continue

            for invite in invites:
                user = invite.user
                # Create user if status is WAITING_LIST, user is None, and event_slug matches
                if invite.status == "WAITING_LIST" and user is None:
                    # Use first_name and last_name if available, else empty string
                    first_name = invite.first_name or ''
                    last_name = invite.last_name or ''
                    # Create user with unusable password
                    user = User(
                        username=invite.email,
                        email=invite.email,
                        first_name=first_name,
                        last_name=last_name,
                    )
                    user.save()
                    invite.user = user
                    invite.save()
                    print(f'Created user {user.id} for invite {invite.id} (WAITING_LIST).')
                if not user:
                    print(f'UserInvite {invite.id} has no user attached.')
                    continue
                # Avoid duplicate checkins
                exists = EventCheckin.objects.filter(event=event, attendee=user).exists()
                if exists:
                    print(f'EventCheckin already exists for user {user.id} and event {event.id}.')
                    continue
                with transaction.atomic():
                    EventCheckin.objects.create(event=event, attendee=user, email=user.email)
                    created_count += 1
                    print(f'Created EventCheckin for user {user.id} and event {event.id}.')
        print(f'Total EventCheckins created: {created_count}') 