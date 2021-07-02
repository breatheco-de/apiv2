from django.contrib.auth.models import User
from django.db.models import Q
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from breathecode.admissions.models import Cohort, CohortUser
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
    "breathecode_login": 'Every time it logs in',
    "online_platform_registration": 'First day using breathecode',
    "public_event_attendance": 'Attendy on an eventbrite event',
    "classroom_attendance": 'When the student attent to class',
    "classroom_unattendance": 'When the student miss class',
    "lesson_opened": 'When a lessons is opened on the platform',
    "office_attendance": 'When the office raspberry pi detects the student',
    "nps_survey_answered": 'When a nps survey is answered by the student',
    "exercise_success": 'When student successfuly tests exercise',
    "academy_registration": 'When student successfuly join to academy',
}

ACTIVITY_PUBLIC_SLUGS = [
    'breathecode_login',
    'online_platform_registration',
]


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


class ActivityClassroomView(APIView):
    @capable_of('classroom_activity')
    def post(self, request, cohort_id=None, academy_id=None):

        is_teacher = CohortUser.objects.filter(
            user__id=request.user.id).filter(
                Q(role='TEACHER') | Q(role='ASSISTANT')).first()
        if is_teacher is None:
            raise ValidationException(
                "Only teachers or assistants from this cohort can report classroom activities on the student timeline"
            )

        data = request.data
        if isinstance(data, list) == False:
            data = [data]

        new_activities = []
        for activity in data:
            student_id = activity['user_id']
            del activity['user_id']
            cohort_user = CohortUser.objects.filter(role='STUDENT', user__id=student_id)
            
            # filter by cohort id or slug depending on input
            if isinstance(cohort_id,str):
                cohort_user = cohort_user.filter(cohort__slug=cohort_id)
            else:
                cohort_user = cohort_user.filter(cohort__id=cohort_id)

            cohort_user = cohort_user.first()
            if cohort_user is None:
                raise ValidationException(f"Student {student_id} not found in this cohort {cohort_id}",
                                          slug="not-found-in-cohort")

            new_activities.append(
                add_student_activity(cohort_user.user, activity, academy_id))

        return Response(new_activities, status=status.HTTP_201_CREATED)


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
        if isinstance(data['cohort'], str):
            _query = _query.filter(slug=data['cohort'])
        elif isinstance(data['cohort'], int):
            _query = _query.filter(id=data['cohort'])
        else:
            raise ValidationException('Invalid cohort parameter format')

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
