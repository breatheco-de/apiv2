import json

from django.contrib.auth.models import User
from django.db.models import Avg, Count, Q, Sum
from google.cloud import bigquery
from google.cloud.ndb.query import OR
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from breathecode.activity.models import StudentActivity
from breathecode.activity.serializers import ActivitySerializer
from breathecode.admissions.models import Cohort, CohortUser
from breathecode.authenticate.actions import get_user_language
from breathecode.services.google_cloud.big_query import BigQuery
from breathecode.utils import HeaderLimitOffsetPagination, capable_of, getLogger
from breathecode.utils.i18n import translation
from capyc.rest_framework.exceptions import ValidationException

from .utils import (
    generate_created_at,
    validate_activity_fields,
    validate_activity_have_correct_data_field,
    validate_if_activity_need_field_cohort,
    validate_if_activity_need_field_data,
    validate_require_activity_fields,
)

# Create your views here.

# DOCUMENTATION RESOURCES
# https://www.programcreek.com/python/example/88825/google.cloud.datastore.Entity
# https://cloud.google.com/datastore/docs/concepts/entities
# https://googleapis.dev/python/datastore/latest/index.html

logger = getLogger(__name__)

ACTIVITIES = {
    "breathecode_login": "Every time it logs in",
    "online_platform_registration": "First day using breathecode",
    "public_event_attendance": "Attendy on an eventbrite event",
    "classroom_attendance": "When the student attent to class",
    "classroom_unattendance": "When the student miss class",
    "lesson_opened": "When a lessons is opened on the platform",
    "office_attendance": "When the office raspberry pi detects the student",
    "nps_survey_answered": "When a nps survey is answered by the student",
    "exercise_success": "When student successfully tests exercise",
    "registration": "When student successfully joins breathecode",
    "educational_status_change": "Student cohort changes like: starts, drop, postpone, etc",
    "educational_note": "Notes that can be added by teachers, TA's or anyone involved in the student education",
    "career_note": "Notes related to the student career",
}

ACTIVITY_PUBLIC_SLUGS = [
    "breathecode_login",
    "online_platform_registration",
]


class ActivityViewMixin(APIView):
    queryargs = []

    def filter_by_slugs(self):
        slugs = self.request.GET.get("slug", [])
        if slugs:
            slugs = slugs.split(",")

        for slug in slugs:
            if slug and slug not in ACTIVITIES:
                raise ValidationException(f"Activity type {slug} not found", slug="activity-not-found")

        if len(slugs) > 1:
            self.queryargs.append(OR(*[StudentActivity.slug == slug for slug in slugs]))
        elif len(slugs) == 1:
            self.queryargs.append(StudentActivity.slug == slugs[0])

    def filter_by_cohort(self, academy_id, cohort_id_or_slug):
        if Cohort.objects.filter(academy__id=academy_id, slug=cohort_id_or_slug).exists():
            self.queryargs.append(StudentActivity.cohort == cohort_id_or_slug)
            return

        try:
            # this parse prevent a call to the db if the cohort slug doesn't exist
            cohort_id = int(cohort_id_or_slug)
        except Exception:
            raise ValidationException("Cohort not found", slug="cohort-not-found")

        slug = Cohort.objects.filter(academy__id=academy_id, pk=cohort_id).values_list("slug", flat=True).first()
        if not slug:
            raise ValidationException("Cohort not found", slug="cohort-not-found")

        self.queryargs.append(StudentActivity.cohort == slug)

    def filter_by_cohorts(self, academy_id):
        cohorts = self.request.GET.get("cohort", [])
        slugs = []
        if cohorts:
            cohorts = cohorts.split(",")

        for cohort in cohorts:
            if cohort and not Cohort.objects.filter(slug=cohort, academy__id=academy_id).exists():
                try:
                    # this parse prevent a call to the db if the cohort slug doesn't exist
                    cohort_id = int(cohort)

                    c = Cohort.objects.filter(id=cohort_id, academy__id=academy_id).first()
                    if not c:
                        raise ValidationException("Cohort not found", slug="cohort-not-found")

                    slugs.append(c.slug)

                except Exception:
                    raise ValidationException("Cohort not found", slug="cohort-not-found")

            slugs.append(cohort)

        if len(slugs) > 1:
            self.queryargs.append(OR(*[StudentActivity.cohort == cohort for cohort in slugs]))
        elif len(slugs) == 1:
            self.queryargs.append(StudentActivity.cohort == slugs[0])

    def filter_by_user_ids(self):
        user_ids = self.request.GET.get("user_id", [])
        if user_ids:
            user_ids = user_ids.split(",")

        for user_id in user_ids:
            try:
                int(user_id)
            except ValueError:
                raise ValidationException("user_id is not a integer", slug="bad-user-id")

        for user_id in user_ids:
            if not User.objects.filter(id=user_id).exists():
                raise ValidationException("User not exists", slug="user-not-exists")

        if len(user_ids) > 1:
            self.queryargs.append(OR(*[StudentActivity.user_id == int(user_id) for user_id in user_ids]))
        elif len(user_ids) == 1:
            self.queryargs.append(StudentActivity.user_id == int(user_ids[0]))

    def filter_by_emails(self):
        emails = self.request.GET.get("email", [])
        if emails:
            emails = emails.split(",")

        for email in emails:
            if not User.objects.filter(email=email).exists():
                raise ValidationException("User not exists", slug="user-not-exists")

        if len(emails) > 1:
            self.queryargs.append(OR(*[StudentActivity.email == email for email in emails]))
        elif len(emails) == 1:
            self.queryargs.append(StudentActivity.email == emails[0])

    def get_limit_from_query(self):
        limit = self.request.GET.get("limit")

        if limit is not None:
            limit = int(limit)

        return limit

    def get_offset_from_query(self):
        offset = self.request.GET.get("offset")

        if offset is not None:
            offset = int(offset)

        return offset


class ActivityTypeView(APIView):

    def get_activity_object(self, slug):
        return {"slug": slug, "description": ACTIVITIES[slug]}

    @capable_of("read_activity")
    def get(self, request, activity_slug=None, academy_id=None):
        if activity_slug:
            if activity_slug not in ACTIVITIES:
                raise ValidationException(f"Activity type {activity_slug} not found", slug="activity-not-found")

            res = self.get_activity_object(activity_slug)
            return Response(res)

        res = [self.get_activity_object(slug) for slug in ACTIVITIES.keys()]
        return Response(res)


class ActivityCohortView(ActivityViewMixin, HeaderLimitOffsetPagination):

    @capable_of("read_activity")
    def get(self, request, cohort_id=None, academy_id=None):
        self.queryargs = []
        from breathecode.utils import NDB

        self.filter_by_slugs()
        self.filter_by_cohort(academy_id, cohort_id)
        limit = self.get_limit_from_query()
        offset = self.get_offset_from_query()

        client = NDB(StudentActivity)
        data = client.fetch(self.queryargs, limit=limit, offset=offset)
        page = self.paginate_queryset(data, request)

        if self.is_paginate(request):
            count = client.count(self.queryargs)
            return self.get_paginated_response(page, count)
        else:
            return Response(page, status=status.HTTP_200_OK)


class ActivityMeView(APIView):

    @capable_of("read_activity")
    def get(self, request, academy_id=None):
        from breathecode.services.google_cloud import Datastore

        kwargs = {"kind": "student_activity"}

        slug = request.GET.get("slug")
        if slug:
            kwargs["slug"] = slug

        if slug and slug not in ACTIVITIES:
            raise ValidationException(f"Activity type {slug} not found", slug="activity-not-found")

        cohort = request.GET.get("cohort")
        if cohort:
            kwargs["cohort"] = cohort

        if cohort and not Cohort.objects.filter(slug=cohort, academy__id=academy_id).exists():
            raise ValidationException("Cohort not found", slug="cohort-not-found")

        user_id = request.GET.get("user_id")
        if user_id:
            try:
                kwargs["user_id"] = int(user_id)
            except ValueError:
                raise ValidationException("user_id is not a integer", slug="bad-user-id")

        email = request.GET.get("email")
        if email:
            kwargs["email"] = email

        user = User.objects.filter(Q(id=user_id) | Q(email=email))
        if (user_id or email) and not user:
            raise ValidationException("User not exists", slug="user-not-exists")

        datastore = Datastore()

        academy_iter = datastore.fetch(**kwargs, academy_id=int(academy_id))
        public_iter = datastore.fetch(**kwargs, academy_id=0)

        query_iter = academy_iter + public_iter
        query_iter.sort(key=lambda x: x["created_at"], reverse=True)

        return Response(query_iter)

    @capable_of("crud_activity")
    def post(self, request, academy_id=None):

        data = request.data
        user = request.user

        fields = add_student_activity(user, data, academy_id)

        return Response(fields, status=status.HTTP_201_CREATED)


class ActivityClassroomView(APIView, HeaderLimitOffsetPagination):

    @capable_of("classroom_activity")
    def post(self, request, cohort_id=None, academy_id=None):

        cu = CohortUser.objects.filter(user__id=request.user.id).filter(Q(role="TEACHER") | Q(role="ASSISTANT"))

        if cohort_id.isnumeric():
            cu = cu.filter(cohort__id=cohort_id)
        else:
            cu = cu.filter(cohort__slug=cohort_id)

        cu = cu.first()
        if cu is None:
            raise ValidationException(
                "Only teachers or assistants from this cohort can report classroom activities on the student timeline"
            )

        data = request.data
        if isinstance(data, list) == False:
            data = [data]

        new_activities = []
        for activity in data:
            student_id = activity["user_id"]
            del activity["user_id"]
            cohort_user = CohortUser.objects.filter(
                role="STUDENT", user__id=student_id, cohort__id=cu.cohort.id
            ).first()
            if cohort_user is None:
                raise ValidationException("Student not found in this cohort", slug="not-found-in-cohort")

            new_activities.append(add_student_activity(cohort_user.user, activity, academy_id))

        return Response(new_activities, status=status.HTTP_201_CREATED)

    @capable_of("classroom_activity")
    def get(self, request, cohort_id=None, academy_id=None):
        from breathecode.services.google_cloud import Datastore

        kwargs = {"kind": "student_activity"}

        # get the cohort
        cohort = Cohort.objects.filter(academy__id=academy_id)
        if cohort_id.isnumeric():
            cohort = cohort.filter(id=cohort_id)
        else:
            cohort = cohort.filter(slug=cohort_id)
        cohort = cohort.first()
        if cohort is None:
            raise ValidationException(
                f"Cohort {cohort_id} not found at this academy {academy_id}", slug="cohort-not-found"
            )
        kwargs["cohort"] = cohort.slug

        slug = request.GET.get("slug")
        if slug:
            kwargs["slug"] = slug

        if slug and slug not in ACTIVITIES:
            raise ValidationException(f"Activity type {slug} not found", slug="activity-not-found")

        user_id = request.GET.get("user_id")

        if user_id:
            try:
                kwargs["user_id"] = int(user_id)
            except ValueError:
                raise ValidationException("user_id is not a integer", slug="bad-user-id")

        email = request.GET.get("email")
        if email:
            kwargs["email"] = email

        user = User.objects.filter(Q(id=user_id) | Q(email=email))
        if (user_id or email) and not user:
            raise ValidationException("User not exists", slug="user-not-exists")

        datastore = Datastore()
        # academy_iter = datastore.fetch(**kwargs, academy_id=int(academy_id))

        limit = request.GET.get("limit")
        offset = request.GET.get("offset")

        # get the the total entities on db by kind
        if limit is not None or offset is not None:
            count = datastore.count(**kwargs)

        if limit:
            kwargs["limit"] = int(limit)

        if offset:
            kwargs["offset"] = int(offset)

        public_iter = datastore.fetch(
            **kwargs
        )  # TODO: remove this in the future because the academy_id was not present brefore and students didn't have it

        # query_iter = academy_iter + public_iter
        public_iter.sort(key=lambda x: x["created_at"], reverse=True)

        page = self.paginate_queryset(public_iter, request)

        if self.is_paginate(request):
            return self.get_paginated_response(page, count)
        else:
            return Response(page, status=status.HTTP_200_OK)


def add_student_activity(user, data, academy_id):
    from breathecode.services import Datastore

    validate_activity_fields(data)
    validate_require_activity_fields(data)

    slug = data["slug"]
    academy_id = academy_id if slug not in ACTIVITY_PUBLIC_SLUGS else 0

    if slug not in ACTIVITIES:
        raise ValidationException(f"Activity type {slug} not found", slug="activity-not-found")

    validate_if_activity_need_field_cohort(data)
    validate_if_activity_need_field_data(data)
    validate_activity_have_correct_data_field(data)

    if "cohort" in data:
        _query = Cohort.objects.filter(academy__id=academy_id)
        if data["cohort"].isnumeric():
            _query = _query.filter(id=data["cohort"])
        else:
            _query = _query.filter(slug=data["cohort"])

        if not _query.exists():
            raise ValidationException(
                f"Cohort {str(data['cohort'])} doesn't exist in this academy", slug="cohort-not-exists"
            )

    fields = {
        **data,
        "created_at": generate_created_at(),
        "slug": slug,
        "user_id": user.id,
        "email": user.email,
        "academy_id": int(academy_id),
    }

    datastore = Datastore()
    datastore.update("student_activity", fields)

    return fields


class StudentActivityView(APIView, HeaderLimitOffsetPagination):

    @capable_of("read_activity")
    def get(self, request, student_id=None, academy_id=None):
        from breathecode.services.google_cloud import Datastore

        cohort_user = CohortUser.objects.filter(
            role="STUDENT", user__id=student_id, cohort__academy__id=academy_id
        ).first()
        if cohort_user is None:
            raise ValidationException(
                "There is not student with that ID that belongs to any cohort within your academy",
                slug="student-no-cohort",
            )

        kwargs = {"kind": "student_activity"}

        slug = request.GET.get("slug")
        if slug:
            kwargs["slug"] = slug

        if slug and slug not in ACTIVITIES:
            raise ValidationException(f"Activity type {slug} not found", slug="activity-not-found")

        if student_id:
            try:
                kwargs["user_id"] = int(student_id)
            except ValueError:
                raise ValidationException("student_id is not a integer", slug="bad-student-id")

        email = request.GET.get("email")
        if email:
            kwargs["email"] = email

        user = User.objects.filter(Q(id=student_id) | Q(email=email))
        if (student_id or email) and not user:
            raise ValidationException("User not exists", slug="user-not-exists")

        datastore = Datastore()
        # academy_iter = datastore.fetch(**kwargs, academy_id=int(academy_id))

        limit = request.GET.get("limit")
        offset = request.GET.get("offset")

        # get the the total entities on db by kind
        if limit is not None or offset is not None:
            count = datastore.count(**kwargs)

        if limit:
            kwargs["limit"] = int(limit)

        if offset:
            kwargs["offset"] = int(offset)

        public_iter = datastore.fetch(
            **kwargs
        )  # TODO: remove this in the future because the academy_id was not present before and students didn't have it

        # query_iter = academy_iter + public_iter
        public_iter.sort(key=lambda x: x["created_at"], reverse=True)

        page = self.paginate_queryset(public_iter, request)

        if self.is_paginate(request):
            return self.get_paginated_response(page, count)
        else:
            return Response(page, status=status.HTTP_200_OK)

    @capable_of("crud_activity")
    def post(self, request, student_id=None, academy_id=None):

        data = request.data
        if isinstance(data, list) == False:
            data = [data]

        new_activities = []
        for activity in data:

            if "cohort" not in activity:
                raise ValidationException(
                    "Every activity specified for each student must have a cohort (slug)", slug="missing-cohort"
                )
            elif activity["cohort"].isnumeric():
                raise ValidationException("Cohort must be a slug, not a numeric ID", slug="invalid-cohort")

            student_id = activity["user_id"]
            del activity["user_id"]
            cohort_user = CohortUser.objects.filter(
                role="STUDENT", user__id=student_id, cohort__slug=activity["cohort"]
            ).first()
            if cohort_user is None:
                raise ValidationException("Student not found in this cohort", slug="not-found-in-cohort")

            new_activities.append(add_student_activity(cohort_user.user, activity, academy_id))

        return Response(new_activities, status=status.HTTP_201_CREATED)


class V2MeActivityView(APIView):

    def get(self, request, activity_id=None):
        lang = get_user_language(request)
        client, project_id, dataset = BigQuery.client()

        if activity_id:
            # Define a query
            query = f"""
                SELECT *
                FROM `{project_id}.{dataset}.activity`
                WHERE id = @activity_id
                    AND user_id = @user_id
                ORDER BY id DESC
                LIMIT 1
            """

            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("activity_id", "STRING", activity_id),
                    bigquery.ScalarQueryParameter("user_id", "INT64", request.user.id),
                ]
            )

            # Run the query
            query_job = client.query(query, job_config=job_config)
            results = query_job.result()

            result = next(results)
            if not result:
                raise ValidationException(
                    translation(lang, en="activity not found", es="actividad no encontrada", slug="activity-not-found"),
                    code=404,
                )

            serializer = ActivitySerializer(result, many=False)
            return Response(serializer.data)

        limit = int(request.GET.get("limit", 100))
        offset = (int(request.GET.get("page", 1)) - 1) * limit
        kind = request.GET.get("kind", None)

        query = f"""
            SELECT *
            FROM `{project_id}.{dataset}.activity`
            WHERE user_id = @user_id
                {'AND kind = @kind' if kind else ''}
            ORDER BY timestamp DESC
            LIMIT @limit
            OFFSET @offset
        """

        data = [
            bigquery.ScalarQueryParameter("user_id", "INT64", request.user.id),
            bigquery.ScalarQueryParameter("limit", "INT64", limit),
            bigquery.ScalarQueryParameter("offset", "INT64", offset),
        ]

        if kind:
            data.append(bigquery.ScalarQueryParameter("kind", "STRING", kind))

        job_config = bigquery.QueryJobConfig(query_parameters=data)

        # Run the query
        query_job = client.query(query, job_config=job_config)
        results = query_job.result()

        serializer = ActivitySerializer(results, many=True)
        return Response(serializer.data)


class V2AcademyActivityView(APIView):

    @capable_of("read_activity")
    def get(self, request, activity_id=None, academy_id=None):
        lang = get_user_language(request)
        client, project_id, dataset = BigQuery.client()

        user_id = request.GET.get("user_id", None)
        if user_id is None:
            user_id = request.user.id

        if activity_id:
            # Define a query
            query = f"""
                SELECT *
                FROM `{project_id}.{dataset}.activity`
                WHERE id = @activity_id
                    AND user_id = @user_id
                    AND meta.academy = @academy_id
                ORDER BY id DESC
                LIMIT 1
            """

            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("activity_id", "STRING", activity_id),
                    bigquery.ScalarQueryParameter("academy_id", "INT64", academy_id),
                    bigquery.ScalarQueryParameter("user_id", "INT64", user_id),
                ]
            )

            # Run the query
            query_job = client.query(query, job_config=job_config)
            results = query_job.result()

            result = next(results)
            if not result:
                raise ValidationException(
                    translation(lang, en="activity not found", es="actividad no encontrada", slug="activity-not-found"),
                    code=404,
                )

            serializer = ActivitySerializer(result, many=False)
            return Response(serializer.data)

        limit = int(request.GET.get("limit", 100))
        offset = (int(request.GET.get("page", 1)) - 1) * limit
        kind = request.GET.get("kind", None)
        date_start = request.GET.get("date_start", None)
        date_end = request.GET.get("date_end", None)

        query = f"""
            SELECT *
            FROM `{project_id}.{dataset}.activity`
            WHERE user_id = @user_id
                AND meta.academy = @academy_id
                {'AND kind = @kind' if kind else ''}
                {'AND timestamp >= @date_start' if date_start else ''}
                {'AND timestamp <= @date_end' if date_end else ''}
            ORDER BY timestamp DESC
            LIMIT @limit
            OFFSET @offset
        """

        data = [
            bigquery.ScalarQueryParameter("academy_id", "INT64", int(academy_id)),
            bigquery.ScalarQueryParameter("user_id", "INT64", user_id),
            bigquery.ScalarQueryParameter("limit", "INT64", limit),
            bigquery.ScalarQueryParameter("offset", "INT64", offset),
        ]

        if kind:
            data.append(bigquery.ScalarQueryParameter("kind", "STRING", kind))

        if date_start:
            data.append(bigquery.ScalarQueryParameter("date_start", "TIMESTAMP", date_start))

        if date_end:
            data.append(bigquery.ScalarQueryParameter("date_end", "TIMESTAMP", date_end))

        job_config = bigquery.QueryJobConfig(query_parameters=data)

        # Run the query
        query_job = client.query(query, job_config=job_config)
        results = query_job.result()

        serializer = ActivitySerializer(results, many=True)
        return Response(serializer.data)


class V2AcademyActivityReportView(APIView):

    @capable_of("read_activity")
    def get(self, request, academy_id=None):
        query = request.GET.get("query", "{}")

        query = json.loads(query)
        result = BigQuery.table("activity")

        fields = request.GET.get("fields", None)
        if fields is not None:
            result = result.select(*fields.split(","))

        by = request.GET.get("by", None)
        if by is not None:
            result = result.group_by(*by.split(","))

        order = request.GET.get("order", None)
        if order is not None:
            result = result.order_by(*order.split(","))

        limit = request.GET.get("limit", None)
        if limit is not None:
            result = result.limit_by(limit)

        if "filter" in query:
            result = result.filter(**query["filter"])

        if "grouping_function" in query:
            grouping_function = query["grouping_function"]
            aggs = []
            if "sum" in grouping_function:
                for value in grouping_function["sum"]:
                    aggs.append(Sum(value))

            if "count" in grouping_function:
                for value in grouping_function["count"]:
                    aggs.append(Count(value))

            if "avg" in grouping_function:
                for value in grouping_function["avg"]:
                    aggs.append(Avg(value))

            result = result.aggregate(*aggs)
        else:
            result = result.build()

        data = []
        for r in result:
            data.append(dict(r.items()))

        return Response(data)
