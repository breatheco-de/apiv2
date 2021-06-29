from django.contrib.auth.models import User
from django.db.models import Q
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from breathecode.admissions.models import Cohort
from breathecode.utils import ValidationException, capable_of

from .utils import (generate_created_at, validate_activity_fields,
                    validate_activity_have_correct_data_field,
                    validate_if_activity_need_field_cohort,
                    validate_if_activity_need_field_data,
                    validate_require_activity_fields)

# Create your views here.

# DOCUMENTATION RESOURCES
# https://www.programcreek.com/python/example/88825/google.cloud.datastore.Entity
# https://cloud.google.com/datastore/docs/concepts/entities
# https://googleapis.dev/python/datastore/latest/index.html

ACTIVITIES = {
    "breathecode-login": 'Every time it logs in',
    "online-platform-registration": 'First day using breathecode',
    "public-event-attendance": 'Attendy on an eventbrite event',
    "classroom-attendance": 'When the student attent to class',
    "classroom-unattendance": 'When the student miss class',
    "lesson-opened": 'When a lessons is opened on the platform',
    "office-attendance": 'When the office raspberry pi detects the student',
    "nps-survey-answered": 'When a nps survey is answered by the student',
    "exercise-success": 'When student successfuly tests exercise',
    "academy-registration": 'When student successfuly join to academy',
}

ACTIVITY_PUBLIC_SLUGS = [
    'breathecode-login',
    'online-platform-registration',
]


class ActivityTypeView(APIView):
    def get_activity_object(self, slug):
        return {'slug': slug, 'description': ACTIVITIES[slug]}

    @capable_of('read_activity')
    def get(self, request, activity_slug=None, academy_id=None):
        if activity_slug:
            if activity_slug not in ACTIVITIES:
                raise ValidationException('Activity type not found',
                                          slug='activity-not-found')

            res = self.get_activity_object(activity_slug)
            return Response(res)

        res = [self.get_activity_object(slug) for slug in ACTIVITIES.keys()]
        return Response(res)


class ActivityView(APIView):
    @capable_of('read_activity')
    def get(self, request, academy_id=None):
        from breathecode.services.google_cloud import Datastore

        kwargs = {'kind': 'student_activity'}

        slug = request.GET.get('slug')
        if slug:
            kwargs['slug'] = slug

        if slug and slug not in ACTIVITIES:
            raise ValidationException('Activity type not found',
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
        academy_iter = datastore.fetch(**kwargs, academy_id=int(academy_id))
        public_iter = datastore.fetch(**kwargs, academy_id=0)

        query_iter = academy_iter + public_iter
        query_iter.sort(key=lambda x: x['created_at'], reverse=True)

        return Response(query_iter)

    @capable_of('crud_activity')
    def post(self, request, academy_id=None):
        from breathecode.services import Datastore

        data = request.data
        user = request.user

        validate_activity_fields(data)
        validate_require_activity_fields(data)

        slug = data['slug']
        academy_id = academy_id if slug not in ACTIVITY_PUBLIC_SLUGS else 0

        if slug not in ACTIVITIES:
            raise ValidationException('Activity type not found',
                                      slug='activity-not-found')

        validate_if_activity_need_field_cohort(data)
        validate_if_activity_need_field_data(data)
        validate_activity_have_correct_data_field(data)

        if 'cohort' in data and not Cohort.objects.filter(
                slug=data['cohort'], academy__id=academy_id).exists():
            raise ValidationException('Cohort not exists',
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

        return Response(fields, status=status.HTTP_201_CREATED)
