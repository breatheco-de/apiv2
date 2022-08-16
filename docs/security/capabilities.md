# Capabilities

Authenticated users must belong to at least one academy with a specific role, each role has a series of capabilities that specify what any user with that role will be "capable" of doing.

Authenticated methods must be decorated with the `@capable_of` decorator in increase security validation. For example:

```python
    from breathecode.utils import capable_of
    @capable_of('crud_member')
    def post(self, request, academy_id=None):
        serializer = StaffPOSTSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
```

Any view decorated with the @capable_of must be used passing an academy id either:

1. Anywhere on the endpoint url, E.g: `path('academy/<int:academy_id>/member', MemberView.as_view()),`
2. Or on the request header using the `Academy` header.

## Available capabilities:

This list is alive, it will grow and vary over time:

```py
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
        'slug': 'crud_invite',
        'description': 'Create, update or delete invites from users'
    },
    {
        'slug': 'invite_resend',
        'description': 'Resent invites for user academies'
    },
    {
        'slug': 'read_assignment',
        'description': 'Read assignment information'
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
        'slug': 'read_assignment',
        'description': 'List all the assignments'
    },
    {
        'slug': 'crud_assignment',
        'description': 'Create, update or delete a assignment'
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
        'slug': 'crud_mentorship_mentor',
        'description': 'Create, delete or update all mentorship mentors from one academy'
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
        'slug': 'read_asset',
        'description': 'Read all academy registry assets'
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
    {
        'slug': 'get_gitpod_user',
        'description': 'List gitpod user the academy is consuming'
    },
    {
        'slug': 'update_gitpod_user',
        'description': 'Update gitpod user expiration based on available information'
    },
    {
        'slug': 'read_technology',
        'description': 'Read asset technologies'
    },
    {
        'slug': 'crud_technology',
        'description': 'Update, create and delete asset technologies'
    },
    {
        'slug': 'read_keyword',
        'description': 'Read SEO keywords'
    },
    {
        'slug': 'crud_keyword',
        'description': 'Update, create and delete SEO keywords'
    },
    {
        'slug': 'read_keywordcluster',
        'description': 'Update, create and delete asset technologies'
    },
    {
        'slug': 'crud_keywordcluster',
        'description': 'Update, create and delete asset technologies'
    },
]
```
