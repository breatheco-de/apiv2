import os, requests, sys, pytz
from typing import TypedDict
from datetime import datetime
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand, CommandError
from django.contrib.contenttypes.models import ContentType

from ...models import Capability, Role

PERMISSIONS = [{
    'slug': 'search_mentorships',
    'app': 'Mentorships',
    'description': 'List mentorships for taking or giving'
}, {
    'slug': 'receive_mentorhips',
    'description': 'Allows to join a live session as a mentee, and rate a mentoring session'
}, {
    'slug': 'give_mentorships',
    'description': 'Allows to join a live session as a mentor and close the session afterwards'
}]

GROUPS = [
    {
        'slug': 'superadmin',
        'name': 'Super Admin',
        'features': [c['slug'] for c in PERMISSIONS],
    },
    {
        'slug': 'user',
        'name': 'Logged In User',
        'features': [],
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


def get_permissions():
    # prevent edit the constant
    return PERMISSIONS.copy()


def get_groups():
    # prevent edit the constant
    return GROUPS.copy()


def remove_duplicates(slugs):
    return list(dict.fromkeys(slugs))


class Command(BaseCommand):
    help = 'Create default system groups and permissions based on features'

    def handle(self, *args, **options):

        # Here is a list of all the current permissions in the system
        permissions = get_permissions()

        for p in permissions:
            _per = Permission.objects.filter(codename=p['slug']).first()
            if _per is None:
                #content_type = ContentType.objects.get(app_label='app_name', model='model_name')
                _per = Permission(name=p['slug'], codename=p['slug'])
                _per.save()

        # # # These are the MAIN roles, they cannot be deleted by anyone at the academy.
        # groups = get_groups()

        # for g in groups:
        #     _g = Group.objects.filter(name=g['slug']).first()
        #     if _g is None:
        #         _g = Group(name=_g['name'])
        #         _g.save()

        #     _g.permissions.clear()
        #     g['features'] = remove_duplicates(g['features'])
        #     for c in g['features']:
        #         _g.permissions.add(c)
