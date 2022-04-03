import os, requests, sys, pytz
from typing import TypedDict
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError

from ...models import Capability, Role

FEATURES = [
    {
        'slug': 'search_mentorships',
        'description': 'List mentorships for taking or giving'
    },
    {
        'slug': 'receive_mentorhips',
        'description': 'Allows to join a live session as a mentee, and rate a mentoring session'
    },
    {
        'slug': 'give_mentorships',
        'description': 'Allows to join a live session as a mentor and close the session afterwards'
    },
    {
        'slug':
        'superadmin',
        'description':
        'Used only for super administators and allows duing very specific maintance operations like replacing a syllabus asset slug'
    },
]

GROUPS = [
    {
        'slug': 'superadmin',
        'name': 'Super Admin',
        'features': [c['slug'] for c in FEATURES],
    },
    {
        'slug': 'user',
        'name': 'Logged In User',
        'features': [
            'read_events',
            'read_events',
        ],
    },
    {
        'slug': 'mentee',
        'name': 'Mentee',
        'features': [
            'search_mentorships',
            'receive_mentorhips',
        ],
    },
    {
        'slug': 'mentor',
        'name': 'Mentor',
        'features': [
            'search_mentorships',
            'give_mentorhips',
        ],
    },
]


def get_features():
    # prevent edit the constant
    return CAPABILITIES.copy()


def get_roles():
    # prevent edit the constant
    return GROUPS.copy()


class Command(BaseCommand):
    help = 'Create default system capabilities'

    def handle(self, *args, **options):

        # Here is a list of all the current capabilities in the system
        features = get_features()

        # for f in features:
        #     _cap = Capability.objects.filter(slug=c['slug']).first()
        #     if _cap is None:
        #         _cap = Capability(**c)
        #         _cap.save()
        #     else:
        #         _cap.description = c['description']
        #         _cap.save()

        # # These are the MAIN roles, they cannot be deleted by anyone at the academy.
        # roles = get_roles()

        # # These are additional roles that extend from the base roles above,
        # # you can exend from more than one role but also add additional capabilitis at the end
        # extend_roles(roles)

        # for r in roles:
        #     _r = Role.objects.filter(slug=r['slug']).first()
        #     if _r is None:
        #         _r = Role(slug=r['slug'], name=r['name'])
        #         _r.save()

        #     _r.capabilities.clear()
        #     r['caps'] = remove_duplicates(r['caps'])
        #     for c in r['caps']:
        #         _r.capabilities.add(c)
