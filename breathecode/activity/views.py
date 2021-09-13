from breathecode.activity.models import Activity
from django.contrib.auth.models import User
from django.db.models import Q
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from breathecode.admissions.models import Cohort, CohortUser
from breathecode.utils import ValidationException, capable_of
from breathecode.utils import HeaderLimitOffsetPagination

from .utils import (generate_created_at, validate_activity_fields,
                    validate_activity_have_correct_data_field,
                    validate_if_activity_need_field_cohort,
                    validate_if_activity_need_field_data,
                    validate_require_activity_fields)

from google.cloud.ndb.query import OR

# Create your views here.

# DOCUMENTATION RESOURCES
# https://www.programcreek.com/python/example/88825/google.cloud.datastore.Entity
# https://cloud.google.com/datastore/docs/concepts/entities
# https://googleapis.dev/python/datastore/latest/index.html

ACTIVITIES = {
    'breathecode_login': 'Every time it logs in',
    'online_platform_registration': 'First day using breathecode',
    'public_event_attendance': 'Attendy on an eventbrite event',
    'classroom_attendance': 'When the student attent to class',
    'classroom_unattendance': 'When the student miss class',
    'lesson_opened': 'When a lessons is opened on the platform',
    'office_attendance': 'When the office raspberry pi detects the student',
    'nps_survey_answered': 'When a nps survey is answered by the student',
    'exercise_success': 'When student successfuly tests exercise',
    'academy_registration': 'When student successfuly join to academy',
}

ACTIVITY_PUBLIC_SLUGS = [
    'breathecode_login',
    'online_platform_registration',
]


class ActivityViewMixin(APIView):
    queryargs = []

    def filter_by_slugs(self):
        slugs = self.request.GET.get('slug', [])
        if slugs:
            slugs = slugs.split(',')

        for slug in slugs:
            if slug and slug not in ACTIVITIES:
                raise ValidationException(f'Activity type {slug} not found',
                                          slug='activity-not-found')

        if len(slugs) > 1:
            self.queryargs.append(
                OR(*[Activity.slug == slug for slug in slugs]))
        elif len(slugs) == 1:
            self.queryargs.append(Activity.slug == slugs[0])

    def filter_by_cohort(self, cohort):

        query_cohort = Cohort.objects.filter(slug=cohort)

        if query_cohort.count() > 0:
            self.queryargs.append(Activity.cohort == cohort)
        else:
            cohort_id = int(cohort)
            query_cohort = Cohort.objects.get(pk=cohort_id)
            self.queryargs.append(Activity.cohort == query_cohort.slug)

    def filter_by_cohorts(self, academy_id):
        cohorts = self.request.GET.get('cohort', [])
        if cohorts:
            cohorts = cohorts.split(',')

        for cohort in cohorts:
            if (cohort and not Cohort.objects.filter(
                    slug=cohort, academy__id=academy_id).exists()):
                raise ValidationException('Cohort not found',
                                          slug='cohort-not-found')

        if len(cohorts) > 1:
            self.queryargs.append(
                OR(*[Activity.cohort == cohort for cohort in cohorts]))
        elif len(cohorts) == 1:
            self.queryargs.append(Activity.cohort == cohorts[0])

    def filter_by_user_ids(self):
        user_ids = self.request.GET.get('user_id', [])
        if user_ids:
            user_ids = user_ids.split(',')

        for user_id in user_ids:
            try:
                int(user_id)
            except ValueError:
                raise ValidationException('user_id is not a interger',
                                          slug='bad-user-id')

        for user_id in user_ids:
            if not User.objects.filter(id=user_id).exists():
                raise ValidationException('User not exists',
                                          slug='user-not-exists')

        if len(user_ids) > 1:
            self.queryargs.append(
                OR(*[Activity.user_id == int(user_id)
                     for user_id in user_ids]))
        elif len(user_ids) == 1:
            self.queryargs.append(Activity.user_id == int(user_ids[0]))

    def filter_by_emails(self):
        emails = self.request.GET.get('email', [])
        if emails:
            emails = emails.split(',')

        for email in emails:
            if not User.objects.filter(email=email).exists():
                raise ValidationException('User not exists',
                                          slug='user-not-exists')

        if len(emails) > 1:
            self.queryargs.append(
                OR(*[Activity.email == email for email in emails]))
        elif len(emails) == 1:
            self.queryargs.append(Activity.email == emails[0])

    def get_limit_from_query(self):
        limit = self.request.GET.get('limit')

        if limit is not None:
            limit = int(limit)

        return limit

    def get_offset_from_query(self):
        offset = self.request.GET.get('offset')

        if offset is not None:
            offset = int(offset)

        return offset


class ActivityTypeView(APIView):
    def get_activity_object(self, slug):
        return {'slug': slug, 'description': ACTIVITIES[slug]}

    @capable_of('read_activity')
    def get(self, request, activity_slug=None, academy_id=None):
        if activity_slug:
            if activity_slug not in ACTIVITIES:
                raise ValidationException(
                    f'Activity type {activity_slug} not found',
                    slug='activity-not-found')

            res = self.get_activity_object(activity_slug)
            return Response(res)

        res = [self.get_activity_object(slug) for slug in ACTIVITIES.keys()]
        return Response(res)


class ActivityCohortView(ActivityViewMixin, HeaderLimitOffsetPagination):
    def get(self, request, cohort_id=None):
        from google.cloud import ndb
        client = ndb.Client()

        self.filter_by_slugs()
        self.filter_by_cohort(cohort_id)
        limit = self.get_limit_from_query()
        offset = self.get_offset_from_query()

        with client.context():
            query = Activity.query().filter(*self.queryargs, )

            elements = query.fetch(limit=limit, offset=offset)
            activities = [c.to_dict() for c in elements]

        return Response(activities, status=status.HTTP_200_OK)


class ActivityMeView(APIView):
    @capable_of('read_activity')
    def get(self, request, academy_id=None):
        from breathecode.services.google_cloud import Datastore

        kwargs = {'kind': 'student_activity'}

        slug = request.GET.get('slug')
        if slug:
            kwargs['slug'] = slug

        if slug and slug not in ACTIVITIES:
            raise ValidationException(f'Activity type {slug} not found',
                                      slug='activity-not-found')

        cohort = request.GET.get('cohort')
        if cohort:
            kwargs['cohort'] = cohort

        if (cohort and not Cohort.objects.filter(
                slug=cohort, academy__id=academy_id).exists()):
            raise ValidationException('Cohort not found',
                                      slug='cohort-not-found')

        user_id = request.GET.get('user_id')
        if user_id:
            try:
                kwargs['user_id'] = int(user_id)
            except ValueError:
                raise ValidationException('user_id is not a interger',
                                          slug='bad-user-id')

        email = request.GET.get('email')
        if email:
            kwargs['email'] = email

        user = User.objects.filter(Q(id=user_id) | Q(email=email))
        if (user_id or email) and not user:
            raise ValidationException('User not exists',
                                      slug='user-not-exists')

        datastore = Datastore()

        # limit = request.GET.get('limit')
        # if limit:
        #     kwargs['limit'] = int(limit)

        # offset = request.GET.get('offset')
        # if offset:
        #     kwargs['offset'] = int(offset)

        academy_iter = datastore.fetch(**kwargs, academy_id=int(academy_id))
        public_iter = datastore.fetch(**kwargs, academy_id=0)

        query_iter = academy_iter + public_iter
        query_iter.sort(key=lambda x: x['created_at'], reverse=True)

        return Response(query_iter)

    @capable_of('crud_activity')
    def post(self, request, academy_id=None):

        data = request.data
        user = request.user

        fields = add_student_activity(user, data, academy_id)

        return Response(fields, status=status.HTTP_201_CREATED)


class ActivityClassroomView(APIView, HeaderLimitOffsetPagination):
    @capable_of('classroom_activity')
    def post(self, request, cohort_id=None, academy_id=None):

        cu = CohortUser.objects.filter(user__id=request.user.id).filter(
            Q(role='TEACHER') | Q(role='ASSISTANT'))

        if cohort_id.isnumeric():
            cu = cu.filter(cohort__id=cohort_id)
        else:
            cu = cu.filter(cohort__slug=cohort_id)

        cu = cu.first()
        if cu is None:
            raise ValidationException(
                'Only teachers or assistants from this cohort can report classroom activities on the student timeline'
            )

        data = request.data
        if isinstance(data, list) == False:
            data = [data]

        new_activities = []
        for activity in data:
            student_id = activity['user_id']
            del activity['user_id']
            cohort_user = CohortUser.objects.filter(
                role='STUDENT', user__id=student_id,
                cohort__id=cu.cohort.id).first()
            if cohort_user is None:
                raise ValidationException('Student not found in this cohort',
                                          slug='not-found-in-cohort')

            new_activities.append(
                add_student_activity(cohort_user.user, activity, academy_id))

        return Response(new_activities, status=status.HTTP_201_CREATED)

    @capable_of('classroom_activity')
    def get(self, request, cohort_id=None, academy_id=None):
        from breathecode.services.google_cloud import Datastore

        kwargs = {'kind': 'student_activity'}

        # get the cohort
        cohort = Cohort.objects.filter(academy__id=academy_id)
        if cohort_id.isnumeric():
            cohort = cohort.filter(id=cohort_id)
        else:
            cohort = cohort.filter(slug=cohort_id)
        cohort = cohort.first()
        if cohort is None:
            raise ValidationException(
                f'Cohort {cohort_id} not found at this academy {academy_id}',
                slug='cohort-not-found')
        kwargs['cohort'] = cohort.slug

        slug = request.GET.get('slug')
        if slug:
            kwargs['slug'] = slug

        if slug and slug not in ACTIVITIES:
            raise ValidationException(f'Activity type {slug} not found',
                                      slug='activity-not-found')

        user_id = request.GET.get('user_id')
        if user_id:
            try:
                kwargs['user_id'] = int(user_id)
            except ValueError:
                raise ValidationException('user_id is not a interger',
                                          slug='bad-user-id')

        email = request.GET.get('email')
        if email:
            kwargs['email'] = email

        user = User.objects.filter(Q(id=user_id) | Q(email=email))
        if (user_id or email) and not user:
            raise ValidationException('User not exists',
                                      slug='user-not-exists')

        datastore = Datastore()
        #academy_iter = datastore.fetch(**kwargs, academy_id=int(academy_id))

        limit = request.GET.get('limit')
        offset = request.GET.get('offset')

        # get the the total entities on db by kind
        if limit is not None or offset is not None:
            count = datastore.count(**kwargs)

        if limit:
            kwargs['limit'] = int(limit)

        if offset:
            kwargs['offset'] = int(offset)

        public_iter = datastore.fetch(
            **kwargs
        )  # TODO: remove this in the future because the academy_id was not present brefore and students didn't have it

        # query_iter = academy_iter + public_iter
        public_iter.sort(key=lambda x: x['created_at'], reverse=True)

        page = self.paginate_queryset(public_iter, request)

        if self.is_paginate(request):
            return self.get_paginated_response(page, count)
        else:
            return Response(page, status=status.HTTP_200_OK)


def add_student_activity(user, data, academy_id):
    from breathecode.services import Datastore

    validate_activity_fields(data)
    validate_require_activity_fields(data)

    slug = data['slug']
    academy_id = academy_id if slug not in ACTIVITY_PUBLIC_SLUGS else 0

    if slug not in ACTIVITIES:
        raise ValidationException(f'Activity type {slug} not found',
                                  slug='activity-not-found')

    validate_if_activity_need_field_cohort(data)
    validate_if_activity_need_field_data(data)
    validate_activity_have_correct_data_field(data)

    if 'cohort' in data:
        _query = Cohort.objects.filter(academy__id=academy_id)
        if data['cohort'].isnumeric():
            _query = _query.filter(id=data['cohort'])
        else:
            _query = _query.filter(slug=data['cohort'])

        if not _query.exists():
            raise ValidationException(
                f"Cohort {str(data['cohort'])} doesn't exist",
                slug='cohort-not-exists')

    fields = {
        **data,
        'created_at': generate_created_at(),
        'slug': slug,
        'user_id': user.id,
        'email': user.email,
        'academy_id': int(academy_id),
    }

    datastore = Datastore()
    datastore.update('student_activity', fields)

    return fields
