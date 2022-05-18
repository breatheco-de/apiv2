import os, requests, sys, pytz
from typing import TypedDict
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError

from ...actions import delete_tokens
from ...models import Capability, Role

CAPABILITIES = [
    {
        'slug': 'read_my_academy',
        'description': 'Read your academy information'
    },
    {
        'slug': 'crud_my_academy',
        'description': 'Read, or update your academy information (very high level, almost the academy admin)'
    },
    {
        'slug': 'crud_member',
        'description': 'Create, update or delete academy members (very high level, almost the academy admin)'
    },
    {
        'slug': 'read_member',
        'description': 'Read academy staff member information'
    },
    {
        'slug': 'crud_student',
        'description': 'Create, update or delete students'
    },
    {
        'slug': 'read_student',
        'description': 'Read student information'
    },
    {
        'slug': 'read_invite',
        'description': 'Read invites from users'
    },
    {
        'slug': 'invite_resend',
        'description': 'Resent invites for user academies'
    },
    {
        'slug': 'read_assignment',
        'description': 'Read assigment information'
    },
    {
        'slug':
        'read_assignment_sensitive_details',
        'description':
        'The mentor in residence is allowed to see aditional info about the task, like the "delivery url"'
    },
    {
        'slug': 'read_shortlink',
        'description': 'Access the list of marketing shortlinks'
    },
    {
        'slug': 'crud_shortlink',
        'description': 'Create, update and delete marketing short links'
    },
    {
        'slug': 'crud_assignment',
        'description': 'Update assignments'
    },
    {
        'slug': 'task_delivery_details',
        'description': 'Get delivery URL for a task, that url can be sent to students for delivery'
    },
    {
        'slug': 'read_certificate',
        'description': 'List and read all academy certificates'
    },
    {
        'slug': 'crud_certificate',
        'description': 'Create, update or delete student certificates'
    },
    {
        'slug': 'read_layout',
        'description': 'Read layouts to generate new certificates'
    },
    {
        'slug': 'read_syllabus',
        'description': 'List and read syllabus information'
    },
    {
        'slug': 'crud_syllabus',
        'description': 'Create, update or delete syllabus versions'
    },
    {
        'slug': 'read_organization',
        'description': 'Read academy organization details'
    },
    {
        'slug': 'crud_organization',
        'description': 'Update, create or delete academy organization details'
    },
    {
        'slug': 'read_event',
        'description': 'List and retrieve event information'
    },
    {
        'slug': 'crud_event',
        'description': 'Create, update or delete event information'
    },
    {
        'slug': 'read_all_cohort',
        'description': 'List all the cohorts or single cohort information'
    },
    {
        'slug': 'read_single_cohort',
        'description': 'single cohort information related to a user'
    },
    {
        'slug': 'crud_cohort',
        'description': 'Create, update or delete cohort info'
    },
    {
        'slug': 'read_eventcheckin',
        'description': 'List and read all the event_checkins'
    },
    {
        'slug': 'read_survey',
        'description': 'List all the nps answers'
    },
    {
        'slug': 'crud_survey',
        'description': 'Create, update or delete surveys'
    },
    {
        'slug': 'read_nps_answers',
        'description': 'List all the nps answers'
    },
    {
        'slug': 'read_lead',
        'description': 'List all the leads'
    },
    {
        'slug': 'read_won_lead',
        'description': 'List all the won leads'
    },
    {
        'slug': 'crud_lead',
        'description': 'Create, update or delete academy leads'
    },
    {
        'slug': 'read_review',
        'description': 'Read review for a particular academy'
    },
    {
        'slug': 'crud_review',
        'description': 'Create, update or delete academy reviews'
    },
    {
        'slug': 'read_media',
        'description': 'List all the medias'
    },
    {
        'slug': 'crud_media',
        'description': 'Create, update or delete academy medias'
    },
    {
        'slug': 'read_media_resolution',
        'description': 'List all the medias resolutions'
    },
    {
        'slug': 'crud_media_resolution',
        'description': 'Create, update or delete academy media resolutions'
    },
    {
        'slug': 'read_cohort_activity',
        'description': 'Read low level activity in a cohort (attendancy, etc.)'
    },
    {
        'slug': 'generate_academy_token',
        'description': 'Create a new token only to be used by the academy'
    },
    {
        'slug': 'get_academy_token',
        'description': 'Read the academy token'
    },
    {
        'slug': 'send_reset_password',
        'description': 'Generate a temporal token and resend forgot password link'
    },
    {
        'slug': 'read_activity',
        'description': 'List all the user activities'
    },
    {
        'slug': 'crud_activity',
        'description': 'Create, update or delete a user activities'
    },
    {
        'slug': 'read_assigment',
        'description': 'List all the assigments'
    },
    {
        'slug': 'crud_assigment',
        'description': 'Create, update or delete a assigment'
    },
    {
        'slug':
        'classroom_activity',
        'description':
        'To report student activities during the classroom or cohorts (Specially meant for teachers)'
    },
    {
        'slug': 'academy_reporting',
        'description': 'Get detailed reports about the academy activity'
    },
    {
        'slug': 'generate_temporal_token',
        'description': 'Generate a temporal token to reset github credential or forgot password'
    },
    {
        'slug': 'read_mentorship_service',
        'description': 'Get all mentorship services from one academy'
    },
    {
        'slug': 'crud_mentorship_service',
        'description': 'Create, delete or update all mentorship services from one academy'
    },
    {
        'slug': 'read_mentorship_mentor',
        'description': 'Get all mentorship mentors from one academy'
    },
    {
        'slug': 'read_mentorship_session',
        'description': 'Get all session from one academy'
    },
    {
        'slug': 'crud_mentorship_session',
        'description': 'Create, delete or update all session from one academy'
    },
    {
        'slug': 'crud_freelancer_bill',
        'description': 'Create, delete or update all freelancer bills from one academy'
    },
    {
        'slug': 'read_freelancer_bill',
        'description': 'Read all all freelancer bills from one academy'
    },
    {
        'slug': 'crud_mentorship_bill',
        'description': 'Create, delete or update all mentroship bills from one academy'
    },
    {
        'slug': 'read_mentorship_bill',
        'description': 'Read all mentroship bills from one academy'
    },
    {
        'slug': 'read_mentor',
        'description': 'Get update academy mentors'
    },
    {
        'slug': 'crud_mentor',
        'description': 'Update, create and delete academy mentors'
    },
    {
        'slug': 'crud_asset',
        'description': 'Update, create and delete registry assets'
    },
    {
        'slug': 'read_tag',
        'description': 'Read marketing tags and their details'
    },
    {
        'slug': 'crud_tag',
        'description': 'Update, create and delete a marketing tag and its details'
    },
]

ROLES = [
    {
        'slug': 'admin',
        'name': 'Admin',
        'caps': [c['slug'] for c in CAPABILITIES],
    },
    {
        'slug':
        'academy_token',
        'name':
        'Academy Token',
        'caps': [
            'read_member',
            'read_syllabus',
            'read_student',
            'read_all_cohort',
            'read_media',
            'read_my_academy',
            'read_invite',
            'read_lead',
            'crud_lead',
            'crud_tag',
            'read_tag',
            'read_review',
            'read_shortlink',
            'read_nps_answers',
            'read_won_lead',
            'read_mentorship_service',
            'read_mentorship_mentor',
        ],
    },
    {
        'slug':
        'staff',
        'name':
        'Staff (Base)',
        'caps': [
            'read_member',
            'read_syllabus',
            'read_student',
            'read_all_cohort',
            'read_media',
            'read_my_academy',
            'read_invite',
            'get_academy_token',
            'crud_activity',
            'read_survey',
            'read_tag',
            'read_layout',
            'read_event',
            'read_certificate',
            'academy_reporting',
            'read_won_lead',
            'read_eventcheckin',
            'read_review',
            'read_activity',
            'read_shortlink',
            'read_mentorship_service',
            'read_mentorship_mentor',
        ],
    },
    {
        'slug':
        'student',
        'name':
        'Student',
        'caps': [
            'crud_assignment',
            'read_syllabus',
            'read_assignment',
            'read_single_cohort',
            'read_my_academy',
            'read_all_cohort',
            'crud_activity',
            'read_mentorship_service',
            'read_mentorship_mentor',
        ],
    },
]


def extend(roles, slugs):
    caps_groups = [item['caps'] for item in roles if item['slug'] in slugs]
    inhered_caps = []
    for roles in caps_groups:
        inhered_caps = inhered_caps + roles
    return list(dict.fromkeys(inhered_caps))


def remove_duplicates(slugs):
    return list(dict.fromkeys(slugs))


# this function is used to can mock the list of capabilities
def get_capabilities():
    # prevent edit the constant
    return CAPABILITIES.copy()


# this function is used to can mock the list of roles
def get_roles():
    # prevent edit the constant
    return ROLES.copy()


class RoleType(TypedDict):
    slug: str
    name: str
    caps: list[str]


# this function is used to can mock the list of roles
def extend_roles(roles: list[RoleType]) -> None:
    """
    These are additional roles that extend from the base roles above,
    you can exend from more than one role but also add additional capabilitis at the end.
    """
    roles.append({
        'slug':
        'assistant',
        'name':
        'Teacher Assistant',
        'caps':
        extend(roles, ['staff']) + [
            'read_assigment',
            'crud_assignment',
            'read_cohort_activity',
            'read_nps_answers',
            'classroom_activity',
            'read_event',
            'task_delivery_details',
            'crud_cohort',
        ]
    })
    roles.append({
        'slug': 'career_support',
        'name': 'Career Support Specialist',
        'caps': extend(roles, ['staff']) + ['read_certificate', 'crud_certificate', 'crud_shortlink']
    })
    roles.append({
        'slug':
        'admissions_developer',
        'name':
        'Admissions Developer',
        'caps':
        extend(roles, ['staff']) + [
            'crud_lead', 'crud_student', 'crud_cohort', 'read_all_cohort', 'read_lead', 'read_activity',
            'invite_resend'
        ]
    })
    roles.append({
        'slug': 'syllabus_coordinator',
        'name': 'Syllabus Coordinator',
        'caps': extend(roles, ['staff']) + ['crud_syllabus', 'crud_media', 'crud_asset']
    })
    roles.append({
        'slug': 'culture_and_recruitment',
        'name': 'Culture and Recruitment',
        'caps': extend(roles, ['staff']) + ['crud_member']
    })
    roles.append({
        'slug':
        'community_manager',
        'name':
        'Manage Syllabus, Exercises and all academy content',
        'caps':
        extend(roles, ['staff']) + [
            'crud_lead', 'read_event', 'crud_event', 'read_eventcheckin', 'read_nps_answers', 'read_lead',
            'read_all_cohort', 'crud_media'
        ]
    })
    roles.append({
        'slug':
        'growth_manager',
        'name':
        'Growth Manager',
        'caps':
        extend(roles, ['staff', 'community_manager']) + [
            'crud_media', 'read_activity', 'read_lead', 'read_won_lead', 'crud_review', 'crud_shortlink',
            'crud_tag'
        ]
    })
    roles.append({
        'slug':
        'accountant',
        'name':
        'Accountant',
        'caps':
        extend(roles, ['staff']) +
        ['read_freelancer_bill', 'crud_freelancer_bill', 'crud_mentorship_bill', 'read_mentorship_bill']
    })
    roles.append({
        'slug': 'homework_reviewer',
        'name': 'Homework Reviewer',
        'caps': extend(roles, ['assistant'])
    })
    roles.append({
        'slug': 'teacher',
        'name': 'Teacher',
        'caps': extend(roles, ['assistant']) + ['crud_cohort']
    })
    roles.append({
        'slug':
        'academy_coordinator',
        'name':
        'Mentor in residence',
        'caps':
        extend(roles, ['teacher']) + [
            'crud_syllabus',
            'crud_cohort',
            'crud_student',
            'crud_survey',
            'read_won_lead',
            'crud_member',
            'send_reset_password',
            'generate_temporal_token',
            'crud_certificate',
            'crud_review',
            'read_assignment_sensitive_details',
            'crud_shortlink',
            'invite_resend',
            'crud_mentor',
            'read_mentor',
            'read_mentorship_service',
            'crud_mentorship_service',
            'read_mentorship_session',
            'crud_mentorship_session',
            'crud_mentorship_bill',
            'read_mentorship_bill',
        ]
    })
    roles.append({
        'slug':
        'country_manager',
        'name':
        'Country Manager',
        'caps':
        extend(roles, [
            'academy_coordinator',
            'student',
            'career_support',
            'growth_manager',
            'admissions_developer',
            'syllabus_coordinator',
            'accountant',
        ]) + [
            'crud_my_academy', 'crud_organization', 'generate_academy_token', 'send_reset_password',
            'generate_temporal_token', 'read_organization'
        ]
    })


class Command(BaseCommand):
    help = 'Create default system capabilities'

    def handle(self, *args, **options):

        # Here is a list of all the current capabilities in the system
        caps = get_capabilities()

        for c in caps:
            _cap = Capability.objects.filter(slug=c['slug']).first()
            if _cap is None:
                _cap = Capability(**c)
                _cap.save()
            else:
                _cap.description = c['description']
                _cap.save()

        # These are the MAIN roles, they cannot be deleted by anyone at the academy.
        roles = get_roles()

        # These are additional roles that extend from the base roles above,
        # you can exend from more than one role but also add additional capabilitis at the end
        extend_roles(roles)

        for r in roles:
            _r = Role.objects.filter(slug=r['slug']).first()
            if _r is None:
                _r = Role(slug=r['slug'], name=r['name'])
                _r.save()

            _r.capabilities.clear()
            r['caps'] = remove_duplicates(r['caps'])
            for c in r['caps']:
                _r.capabilities.add(c)
