import hashlib
import logging
import os

from adrf.views import APIView
from asgiref.sync import sync_to_async
from capyc.core.i18n import translation
from capyc.rest_framework.exceptions import ValidationException
from circuitbreaker import CircuitBreakerError
from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponseRedirect, QueryDict
from django.shortcuts import render
from django.utils import timezone
from linked_services.django.service import Service
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from slugify import slugify
from rest_framework.permissions import IsAuthenticated

import breathecode.activity.tasks as tasks_activity
import breathecode.assignments.tasks as tasks
from breathecode.admissions.models import Cohort, CohortUser
from breathecode.assignments.permissions.consumers import code_revision_service
from breathecode.authenticate.actions import aget_user_language, get_user_language
from breathecode.authenticate.models import ProfileAcademy, Token
from breathecode.registry.models import Asset
from breathecode.services.learnpack import LearnPack
from breathecode.utils import GenerateLookupsMixin, capable_of, num_to_roman, response_207
from breathecode.utils.api_view_extensions.api_view_extensions import APIViewExtensions
from breathecode.utils.decorators import consume, has_permission
from breathecode.utils.decorators.capable_of import acapable_of
from breathecode.utils.multi_status_response import MultiStatusResponse

from .actions import deliver_task, sync_cohort_tasks
from .caches import TaskCache
from .forms import DeliverAssigntmentForm
from .models import FinalProject, Task, UserAttachment, RepositoryDeletionOrder
from .serializers import (
    FinalProjectGETSerializer,
    PostFinalProjectSerializer,
    PostTaskSerializer,
    PUTFinalProjectSerializer,
    PUTTaskSerializer,
    TaskAttachmentSerializer,
    TaskGETDeliverSerializer,
    TaskGETSerializer,
    UserAttachmentSerializer,
    RepositoryDeletionOrderSerializer,
)

# Import FlagManager
from .utils.flags import FlagManager

logger = logging.getLogger(__name__)

MIME_ALLOW = [
    "image/png",
    "image/svg+xml",
    "image/jpeg",
    "image/gif",
    "video/quicktime",
    "video/mp4",
    "audio/mpeg",
    "application/pdf",
    "image/jpg",
    "application/octet-stream",
    "application/json",
    "text/plain",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
]

IMAGES_MIME_ALLOW = ["image/png", "image/svg+xml", "image/jpeg", "image/jpg"]

USER_ASSIGNMENTS_BUCKET = os.getenv("USER_ASSIGNMENTS_BUCKET", None)


class TaskTeacherView(APIView):

    def get(self, request, task_id=None, user_id=None):
        items = Task.objects.all()
        logger.debug(f"Found {items.count()} tasks")

        profile_ids = ProfileAcademy.objects.filter(user=request.user.id).values_list("academy__id", flat=True)
        if not profile_ids:
            raise ValidationException(
                "The quest user must belong to at least one academy to be able to request student tasks",
                code=400,
                slug="without-profile-academy",
            )

        items = items.filter(Q(cohort__academy__id__in=profile_ids) | Q(cohort__isnull=True))

        academy = request.GET.get("academy", None)
        if academy is not None:
            items = items.filter(Q(cohort__academy__slug__in=academy.split(",")) | Q(cohort__isnull=True))

        user = request.GET.get("user", None)
        if user is not None:
            items = items.filter(user__id__in=user.split(","))

        # tasks these cohorts (not the users, but the tasks belong to the cohort)
        cohort = request.GET.get("cohort", None)
        if cohort is not None:
            cohorts = cohort.split(",")
            ids = [x for x in cohorts if x.isnumeric()]
            slugs = [x for x in cohorts if not x.isnumeric()]
            items = items.filter(Q(cohort__slug__in=slugs) | Q(cohort__id__in=ids))

        # tasks from users that belong to these cohort
        stu_cohort = request.GET.get("stu_cohort", None)
        if stu_cohort is not None:
            ids = stu_cohort.split(",")

            stu_cohorts = stu_cohort.split(",")
            ids = [x for x in stu_cohorts if x.isnumeric()]
            slugs = [x for x in stu_cohorts if not x.isnumeric()]

            items = items.filter(
                Q(user__cohortuser__cohort__id__in=ids) | Q(user__cohortuser__cohort__slug__in=slugs),
                user__cohortuser__role="STUDENT",
            )

        edu_status = request.GET.get("edu_status", None)
        if edu_status is not None:
            items = items.filter(user__cohortuser__educational_status__in=edu_status.split(","))

        # tasks from users that belong to these cohort
        teacher = request.GET.get("teacher", None)
        if teacher is not None:
            teacher_cohorts = CohortUser.objects.filter(user__id__in=teacher.split(","), role="TEACHER").values_list(
                "cohort__id", flat=True
            )
            items = items.filter(
                user__cohortuser__cohort__id__in=teacher_cohorts, user__cohortuser__role="STUDENT"
            ).distinct()

        task_status = request.GET.get("task_status", None)
        if task_status is not None:
            items = items.filter(task_status__in=task_status.split(","))

        revision_status = request.GET.get("revision_status", None)
        if revision_status is not None:
            items = items.filter(revision_status__in=revision_status.split(","))

        task_type = request.GET.get("task_type", None)
        if task_type is not None:
            items = items.filter(task_type__in=task_type.split(","))

        items = items.order_by("created_at")

        serializer = TaskGETSerializer(items, many=True)
        return Response(serializer.data)


@api_view(["POST"])
def sync_cohort_tasks_view(request, cohort_id=None):
    item = Cohort.objects.filter(id=cohort_id).first()
    if item is None:
        raise ValidationException("Cohort not found")

    syncronized = sync_cohort_tasks(item)
    if len(syncronized) == 0:
        raise ValidationException("No tasks updated")

    serializer = TaskGETSerializer(syncronized, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


class AssignmentTelemetryView(APIView, GenerateLookupsMixin):
    """
    List all snippets, or create a new snippet.
    """

    # @capable_of('read_assignment_telemetry')
    # def get(self, request, academy_id=None):

    #     learnpack_payload = request.body
    #     items = AssetComment.objects.filter(asset__academy__id=academy_id)
    #     lookup = {}

    #     serializer = AcademyCommentSerializer(items, many=True)
    #     return handler.response(serializer.data)

    @has_permission("upload_assignment_telemetry")
    def post(self, request, academy_id=None):

        merged_data = request.data.copy()
        if isinstance(request.query_params, QueryDict):
            for key, value in request.query_params.items():
                merged_data[key] = value

        webhook = LearnPack.add_webhook_to_log(merged_data)

        if webhook:
            tasks.async_learnpack_webhook.delay(webhook.id)
        else:
            logger.debug("A request cannot be parsed, maybe you should update `LearnPack" ".add_webhook_to_log`")
            logger.debug(request.data)
            return Response(
                "this request couldn't no be processed", status=status.HTTP_400_BAD_REQUEST, content_type="text/plain"
            )

        return Response("ok", content_type="text/plain")


class FinalProjectScreenshotView(APIView):

    def upload(self, request, update=False):
        from ..services.google_cloud import Storage

        lang = get_user_language(request)

        files = request.data.getlist("file")
        names = request.data.getlist("name")

        file = request.data.get("file")
        slugs = []

        for index in range(0, len(files)):
            file = files[index]
            if file.content_type not in IMAGES_MIME_ALLOW:
                raise ValidationException(
                    f'You can upload only files on the following formats: {",".join(IMAGES_MIME_ALLOW)}'
                )

        for index in range(0, len(files)):
            file = files[index]
            name = names[index] if len(names) else file.name
            file_bytes = file.read()
            hash = hashlib.sha256(file_bytes).hexdigest()
            slug = slugify(name)

            slugs.append(slug)
            data = {
                "hash": hash,
                "mime": file.content_type,
            }

            # upload file section
            try:
                storage = Storage()
                cloud_file = storage.file(USER_ASSIGNMENTS_BUCKET, hash)
                cloud_file.upload(file, content_type=file.content_type)
                data["url"] = cloud_file.url()

            except CircuitBreakerError:
                raise ValidationException(
                    translation(
                        lang,
                        en="The circuit breaker is open due to an error, please try again later",
                        es="El circuit breaker está abierto debido a un error, por favor intente más tarde",
                        slug="circuit-breaker-open",
                    ),
                    slug="circuit-breaker-open",
                    data={"service": "Google Cloud Storage"},
                    silent=True,
                    code=503,
                )

        return data

    def post(self, request, user_id=None):
        files = self.upload(request)

        return Response(files)


class FinalProjectMeView(APIView):

    def get(self, request, project_id=None, user_id=None):
        if not user_id:
            user_id = request.user.id

        if project_id is not None:
            item = FinalProject.objects.filter(id=project_id, user__id=user_id).first()
            if item is None:
                raise ValidationException("Project not found", code=404, slug="project-not-found")

            serializer = FinalProjectGETSerializer(item, many=False)
            return Response(serializer.data)

        items = FinalProject.objects.filter(members__id=user_id)

        project_status = request.GET.get("project_status", None)
        if project_status is not None:
            items = items.filter(project_status__in=project_status.split(","))

        members = request.GET.get("members", None)
        if members is not None and isinstance(members, list):
            items = items.filter(members__id__in=members)

        revision_status = request.GET.get("revision_status", None)
        if revision_status is not None:
            items = items.filter(revision_status__in=revision_status.split(","))

        visibility_status = request.GET.get("visibility_status", None)
        if visibility_status is not None:
            items = items.filter(visibility_status__in=visibility_status.split(","))
        else:
            items = items.filter(visibility_status="PUBLIC")

        cohort = request.GET.get("cohort", None)
        if cohort is not None:
            if cohort == "null":
                items = items.filter(cohort__isnull=True)
            else:
                cohorts = cohort.split(",")
                ids = [x for x in cohorts if x.isnumeric()]
                slugs = [x for x in cohorts if not x.isnumeric()]
                items = items.filter(Q(cohort__slug__in=slugs) | Q(cohort__id__in=ids))

        serializer = FinalProjectGETSerializer(items, many=True)
        return Response(serializer.data)

    def post(self, request, user_id=None):

        # only create tasks for yourself
        user_id = request.user.id

        payload = request.data

        if isinstance(request.data, list) == False:
            payload = [request.data]

        members_set = set(payload[0]["members"])
        members_set.add(user_id)
        payload[0]["members"] = list(members_set)

        serializer = PostFinalProjectSerializer(
            data=payload, context={"request": request, "user_id": user_id}, many=True
        )
        if serializer.is_valid():
            serializer.save()
            # tasks.teacher_task_notification.delay(serializer.data['id'])
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, project_id=None):

        def update(_req, data, _id=None, only_validate=True):
            lang = get_user_language(request)

            if _id is None:
                raise ValidationException("Missing project id to update", slug="missing-project-id")

            item = FinalProject.objects.filter(id=_id).first()
            if item is None:
                raise ValidationException("Final Project not found", slug="project-not-found")

            if "cohort" not in data:
                raise ValidationException(
                    translation(
                        lang,
                        en="Final project cohort missing",
                        es="Falta la cohorte del proyecto final",
                        slug="cohort-missing",
                    )
                )
            project_cohort = Cohort.objects.filter(id=data["cohort"]).first()
            staff = ProfileAcademy.objects.filter(
                ~Q(role__slug="student"), academy__id=project_cohort.academy.id, user__id=request.user.id
            ).first()

            if not item.members.filter(id=request.user.id).exists() and staff is None:
                raise ValidationException(
                    translation(
                        lang,
                        en="You are not a member of this project",
                        es="No eres miembro de este proyecto",
                        slug="not-a-member",
                    )
                )

            serializer = PUTFinalProjectSerializer(item, data=data, context={"request": _req})
            if serializer.is_valid():
                if not only_validate:
                    serializer.save()
                return status.HTTP_200_OK, serializer.data
            return status.HTTP_400_BAD_REQUEST, serializer.errors

        if project_id is not None:
            code, data = update(request, request.data, project_id, only_validate=False)
            return Response(data, status=code)

        else:  # project_id is None:

            if isinstance(request.data, list) == False:
                raise ValidationException(
                    "You are trying to update many project at once but you didn't provide a list on the payload",
                    slug="update-without-list",
                )

            for item in request.data:
                if "id" not in item:
                    item["id"] = None
                code, data = update(request, item, item["id"], only_validate=True)
                if code != status.HTTP_200_OK:
                    return Response(data, status=code)

            updated_projects = []
            for item in request.data:
                code, data = update(request, item, item["id"], only_validate=False)
                if code == status.HTTP_200_OK:
                    updated_projects.append(data)

            return Response(updated_projects, status=status.HTTP_200_OK)


class FinalProjectCohortView(APIView):

    @capable_of("read_assignment")
    def get(self, request, academy_id, cohort_id):

        lang = get_user_language(request)

        cohort = Cohort.objects.filter(id=cohort_id).first()
        if cohort is None:
            raise ValidationException(
                translation(lang, en="Cohort not found", es="Cohorte no encontrada", slug="cohort-not-found"), code=404
            )

        items = FinalProject.objects.filter(cohort__id=cohort.id)

        serializer = FinalProjectGETSerializer(items, many=True)
        return Response(serializer.data)

    @capable_of("crud_assignment")
    def put(self, request, academy_id, cohort_id, final_project_id):
        lang = get_user_language(request)

        cohort = Cohort.objects.filter(id=cohort_id).first()
        if cohort is None:
            raise ValidationException(
                translation(lang, en="Cohort not found", es="Cohorte no encontrada", slug="cohort-not-found"), code=404
            )

        item = FinalProject.objects.filter(id=final_project_id).first()
        if item is None:
            raise ValidationException(
                translation(lang, en="Project not found", es="Proyecto no encontrado", slug="project-not-found"),
                code=404,
            )

        serializer = PUTFinalProjectSerializer(item, data=request.data, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SyncTasksView(APIView, GenerateLookupsMixin):

    @capable_of("crud_assignment")
    def get(self, request, cohort_id, academy_id):

        lang = get_user_language(request)

        cohort = Cohort.objects.filter(id=cohort_id).first()

        if cohort is None:
            raise ValidationException(
                translation(
                    lang,
                    en=f"Cohort {cohort_id} not found",
                    es=f"Cohorte {cohort_id} no encontrada",
                    slug="cohort-not-found",
                ),
                code=404,
            )

        students = CohortUser.objects.filter(cohort=cohort, role="STUDENT")

        for student in students:
            tasks.sync_cohort_user_tasks.delay(student.id)

        message = translation(
            lang,
            en="Tasks syncronization initiated successfully. This should take a few minutes",
            es="La sincronización de las actividades inició exitosamente. Esto debería demorar unos minutos",
            slug="tasks-syncing",
        )

        return Response({"message": message}, status=status.HTTP_200_OK)


class CohortTaskView(APIView, GenerateLookupsMixin):
    extensions = APIViewExtensions(cache=TaskCache, sort="-created_at", paginate=True)

    @capable_of("read_assignment")
    def get(self, request, cohort_id, academy_id):
        handler = self.extensions(request)

        cache = handler.cache.get()
        if cache is not None:
            return cache

        items = Task.objects.all()
        lookup = {}

        if isinstance(cohort_id, int) or cohort_id.isnumeric():
            lookup["cohort__id"] = cohort_id
        else:
            lookup["cohort__slug"] = cohort_id

        task_type = request.GET.get("task_type", None)
        if task_type is not None:
            lookup["task_type__in"] = task_type.split(",")

        task_status = request.GET.get("task_status", None)
        if task_status is not None:
            lookup["task_status__in"] = task_status.split(",")

        revision_status = request.GET.get("revision_status", None)
        if revision_status is not None:
            lookup["revision_status__in"] = revision_status.split(",")

        educational_status = request.GET.get("educational_status", None)
        if educational_status is not None:
            lookup["user__cohortuser__educational_status__in"] = educational_status.split(",")

        like = request.GET.get("like", None)
        if like is not None and like != "undefined" and like != "":
            items = items.filter(Q(associated_slug__icontains=slugify(like)) | Q(title__icontains=like))

        # tasks from users that belong to these cohort
        student = request.GET.get("student", None)
        if student is not None:
            lookup["user__cohortuser__user__id__in"] = student.split(",")
            lookup["user__cohortuser__role"] = "STUDENT"

        if educational_status is not None or student is not None:
            items = items.distinct()

        items = items.filter(**lookup)
        items = handler.queryset(items)

        serializer = TaskGETSerializer(items, many=True)
        return handler.response(serializer.data)


class RepositoryDeletionsMeView(APIView):

    def get(self, request):

        user = request.user

        items = RepositoryDeletionOrder.objects.filter(user=user)

        status = request.GET.get("status", None)
        if status is not None:
            status = status.upper()
            items = items.filter(status=status)

        serializer = RepositoryDeletionOrderSerializer(items, many=True)
        return Response(serializer.data)


class TaskMeAttachmentView(APIView):

    @capable_of("read_assignment")
    def get(self, request, task_id, academy_id):

        item = Task.objects.filter(id=task_id).first()
        if item is None:
            raise ValidationException("Task not found", code=404, slug="task-not-found")

        allowed = item.user.id == request.user.id
        if not allowed:
            # request user belongs to the same academy as the cohort
            allowed = item.cohort.academy.id == int(academy_id)

        if not allowed:
            raise PermissionDenied(
                "Attachments can only be reviewed by their authors or the academy staff with read_assignment capability"
            )

        serializer = TaskAttachmentSerializer(item.attachments.all(), many=True)
        return Response(serializer.data)

    def upload(self, request, update=False, mime_allow=None):
        from ..services.google_cloud import Storage

        lang = get_user_language(request)

        files = request.data.getlist("file")
        names = request.data.getlist("name")
        result = {
            "data": [],
            "instance": [],
        }

        file = request.data.get("file")
        slugs = []

        if not file:
            raise ValidationException("Missing file in request", code=400)

        if not len(files):
            raise ValidationException("empty files in request")

        if not len(names):
            for file in files:
                names.append(file.name)

        elif len(files) != len(names):
            raise ValidationException("numbers of files and names not match")

        if mime_allow is None:
            mime_allow = MIME_ALLOW

        # files validation below
        for index in range(0, len(files)):
            file = files[index]
            if file.content_type not in mime_allow:
                raise ValidationException(
                    f'You can upload only files on the following formats: {",".join(mime_allow)}, got {file.content_type}',
                )

        for index in range(0, len(files)):
            file = files[index]
            name = names[index] if len(names) else file.name
            file_bytes = file.read()
            hash = hashlib.sha256(file_bytes).hexdigest()
            slug = str(request.user.id) + "-" + slugify(name)

            slug_number = UserAttachment.objects.filter(slug__startswith=slug).exclude(hash=hash).count() + 1
            if slug_number > 1:
                while True:
                    roman_number = num_to_roman(slug_number, lower=True)
                    slug = f"{slug}-{roman_number}"
                    if not slug in slugs:
                        break
                    slug_number = slug_number + 1

            slugs.append(slug)
            data = {
                "hash": hash,
                "slug": slug,
                "mime": file.content_type,
                "name": name,
                "categories": [],
                "user": request.user.id,
            }

            media = UserAttachment.objects.filter(hash=hash, user__id=request.user.id).first()
            if media:
                data["id"] = media.id
                data["url"] = media.url

            else:
                # upload file section
                try:
                    storage = Storage()
                    cloud_file = storage.file(USER_ASSIGNMENTS_BUCKET, hash)
                    cloud_file.upload(file, content_type=file.content_type)
                    data["url"] = cloud_file.url()

                except CircuitBreakerError:
                    raise ValidationException(
                        translation(
                            lang,
                            en="The circuit breaker is open due to an error, please try again later",
                            es="El circuit breaker está abierto debido a un error, por favor intente más tarde",
                            slug="circuit-breaker-open",
                        ),
                        slug="circuit-breaker-open",
                        data={"service": "Google Cloud Storage"},
                        silent=True,
                        code=503,
                    )

            result["data"].append(data)

        from django.db.models import Q

        query = None
        datas_with_id = [x for x in result["data"] if "id" in x]
        for x in datas_with_id:
            if query:
                query = query | Q(id=x["id"])
            else:
                query = Q(id=x["id"])

        if query:
            result["instance"] = UserAttachment.objects.filter(query)

        return result

    def put(self, request, task_id):

        item = Task.objects.filter(id=task_id, user__id=request.user.id).first()
        if item is None:
            raise ValidationException("Task not found", code=404, slug="task-not-found")

        # TODO: mime types are not being validated on the backend
        upload = self.upload(request, update=True, mime_allow=None)
        serializer = UserAttachmentSerializer(
            upload["instance"], data=upload["data"], context=upload["data"], many=True
        )

        if serializer.is_valid():
            serializer.save()

            for att in serializer.instance:
                item.attachments.add(att)
                item.save()

            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TaskMeView(APIView):
    extensions = APIViewExtensions(cache=TaskCache, cache_per_user=True, paginate=True)

    def get(self, request, task_id=None, user_id=None):
        handler = self.extensions(request)

        cache = handler.cache.get()
        if cache is not None:
            return cache

        if not user_id:
            user_id = request.user.id

        if task_id is not None:
            item = Task.objects.filter(id=task_id, user__id=user_id).first()
            if item is None:
                raise ValidationException("Task not found", code=404, slug="task-not-found")

            serializer = TaskGETSerializer(item, many=False)
            return Response(serializer.data)

        items = Task.objects.filter(user__id=user_id)

        task_type = request.GET.get("task_type", None)
        if task_type is not None:
            items = items.filter(task_type__in=task_type.split(","))

        task_status = request.GET.get("task_status", None)
        if task_status is not None:
            items = items.filter(task_status__in=task_status.split(","))

        revision_status = request.GET.get("revision_status", None)
        if revision_status is not None:
            items = items.filter(revision_status__in=revision_status.split(","))

        cohort = request.GET.get("cohort", None)
        if cohort is not None:
            if cohort == "null":
                items = items.filter(cohort__isnull=True)
            else:
                cohorts = cohort.split(",")
                ids = [x for x in cohorts if x.isnumeric()]
                slugs = [x for x in cohorts if not x.isnumeric()]
                items = items.filter(Q(cohort__slug__in=slugs) | Q(cohort__id__in=ids))

        a_slug = request.GET.get("associated_slug", None)
        if a_slug is not None:
            items = items.filter(associated_slug__in=[p.lower() for p in a_slug.split(",")])

        items = handler.queryset(items)

        serializer = TaskGETSerializer(items, many=True)
        return handler.response(serializer.data)

    def put(self, request, task_id=None):

        def update(_req, data, _id=None, only_validate=True):
            if _id is None:
                raise ValidationException("Missing task id to update", slug="missing=task-id")

            item = Task.objects.filter(id=_id).first()
            if item is None:
                raise ValidationException("Task not found", slug="task-not-found", code=404)

            serializer = PUTTaskSerializer(item, data=data, context={"request": _req})
            if serializer.is_valid():
                if not only_validate:
                    serializer.save()
                    if _req.user.id != item.user.id and item.revision_status != "IGNORED":
                        tasks.student_task_notification.delay(item.id)
                return status.HTTP_200_OK, serializer.data
            return status.HTTP_400_BAD_REQUEST, serializer.errors

        if task_id is not None:
            code, data = update(request, request.data, task_id, only_validate=False)
            return Response(data, status=code)

        else:  # task_id is None:

            if isinstance(request.data, list) == False:
                raise ValidationException(
                    "You are trying to update many tasks at once but you didn't provide a list on the payload",
                    slug="update-whout-list",
                )

            for item in request.data:
                if "id" not in item:
                    item["id"] = None
                code, data = update(request, item, item["id"], only_validate=True)
                if code != status.HTTP_200_OK:
                    return Response(data, status=code)

            updated_tasks = []
            for item in request.data:
                code, data = update(request, item, item["id"], only_validate=False)
                if code == status.HTTP_200_OK:
                    updated_tasks.append(data)

            return Response(updated_tasks, status=status.HTTP_200_OK)

    def post(self, request, user_id=None):

        # only create tasks for yourself
        if user_id is None:
            user_id = request.user.id

        payload = request.data

        if isinstance(request.data, list) == False:
            payload = [request.data]

        serializer = PostTaskSerializer(data=payload, context={"request": request, "user_id": user_id}, many=True)
        if serializer.is_valid():
            tasks = serializer.save()
            # tasks.teacher_task_notification.delay(serializer.data['id'])
            tasks_activity.add_activity.delay(
                request.user.id, "open_syllabus_module", related_type="assignments.Task", related_id=tasks[0].id
            )

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, task_id=None):

        if task_id is not None:
            item = Task.objects.filter(id=task_id).first()
            if item is None:
                raise ValidationException("Task not found", code=404, slug="task-not-found")

            if item.user.id != request.user.id:
                raise ValidationException("Task not found for this user", code=400, slug="task-not-found-for-this-user")

            item.delete()

        else:  # task_id is None:
            ids = request.GET.get("id", "")
            if ids == "":
                raise ValidationException("Missing querystring propery id for bulk delete tasks", slug="missing-id")

            ids_to_delete = [int(id.strip()) if id.strip().isnumeric() else id.strip() for id in ids.split(",")]

            all = Task.objects.filter(id__in=ids_to_delete)
            do_not_belong = all.exclude(user__id=request.user.id)
            belong = all.filter(user__id=request.user.id)

            responses = []

            for task in all:
                if task.id in ids_to_delete:
                    ids_to_delete.remove(task.id)

            if belong:
                responses.append(MultiStatusResponse(code=204, queryset=belong))

            if do_not_belong:
                responses.append(
                    MultiStatusResponse(
                        "Task not found for this user",
                        code=400,
                        slug="task-not-found-for-this-user",
                        queryset=do_not_belong,
                    )
                )

            if ids_to_delete:
                responses.append(
                    MultiStatusResponse("Task not found", code=404, slug="task-not-found", queryset=ids_to_delete)
                )

            if do_not_belong or ids_to_delete:
                response = response_207(responses, "associated_slug")
                belong.delete()
                return response

            belong.delete()

        return Response(None, status=status.HTTP_204_NO_CONTENT)


class TaskMeDeliverView(APIView):

    @capable_of("task_delivery_details")
    def get(self, request, task_id, academy_id):

        item = Task.objects.filter(id=task_id).first()
        if item is None:
            raise ValidationException("Task not found")

        serializer = TaskGETDeliverSerializer(item, many=False)
        return Response(serializer.data)


def deliver_assignment_view(request, task_id, token):

    if request.method == "POST":
        _dict = request.POST.copy()
        form = DeliverAssigntmentForm(_dict)

        if "github_url" not in _dict or _dict["github_url"] == "":
            messages.error(request, "Github URL is required")
            return render(request, "form.html", {"form": form})

        token = Token.objects.filter(key=_dict["token"]).first()
        if token is None or token.expires_at < timezone.now():
            messages.error(request, f'Invalid or expired deliver token {_dict["token"]}')
            return render(request, "form.html", {"form": form})

        task = Task.objects.filter(id=_dict["task_id"]).first()
        if task is None:
            messages.error(request, "Invalid task id")
            return render(request, "form.html", {"form": form})

        deliver_task(
            task=task,
            github_url=_dict["github_url"],
            live_url=_dict["live_url"],
        )

        if "callback" in _dict and _dict["callback"] != "":
            return HttpResponseRedirect(redirect_to=_dict["callback"] + "?msg=The task has been delivered")
        else:
            obj = {}
            if task.cohort:
                obj["COMPANY_INFO_EMAIL"] = task.cohort.academy.feedback_email
                obj["COMPANY_LEGAL_NAME"] = task.cohort.academy.legal_name or task.cohort.academy.name
                obj["COMPANY_LOGO"] = task.cohort.academy.logo_url
                obj["COMPANY_NAME"] = task.cohort.academy.name

                if "heading" not in obj:
                    obj["heading"] = task.cohort.academy.name

            return render(request, "message.html", {"message": "The task has been delivered", **obj})
    else:
        task = Task.objects.filter(id=task_id).first()
        if task is None:
            return render(
                request,
                "message.html",
                {
                    "message": f"Invalid assignment id {str(task_id)}",
                },
            )

        _dict = request.GET.copy()
        _dict["callback"] = request.GET.get("callback", "")
        _dict["token"] = token
        _dict["task_name"] = task.title
        _dict["task_id"] = task.id

        form = DeliverAssigntmentForm(_dict)

        data = {}
        if task.cohort:
            data["COMPANY_INFO_EMAIL"] = task.cohort.academy.feedback_email
            data["COMPANY_LEGAL_NAME"] = task.cohort.academy.legal_name or task.cohort.academy.name
            data["COMPANY_LOGO"] = task.cohort.academy.logo_url
            data["COMPANY_NAME"] = task.cohort.academy.name

            if "heading" not in data:
                data["heading"] = task.cohort.academy.name

    return render(
        request,
        "form.html",
        {
            "form": form,
            # 'heading': 'Deliver project assignment',
            "intro": "Please fill the following information to deliver your assignment",
            "btn_lable": "Deliver Assignment",
            **data,
        },
    )


class SubtaskMeView(APIView):

    def get(self, request, task_id):

        item = Task.objects.filter(id=task_id, user__id=request.user.id).first()
        if item is None:
            raise ValidationException("Task not found", code=404, slug="task-not-found")

        return Response(item.subtasks)

    def put(self, request, task_id):

        item = Task.objects.filter(id=task_id, user__id=request.user.id).first()
        if item is None:
            raise ValidationException("Task not found", code=404, slug="task-not-found")

        if not isinstance(request.data, list):
            raise ValidationException("Subtasks json must be an array of tasks", code=404, slug="json-as-array")

        subtasks_ids = []
        for t in request.data:
            if not "id" in t:
                raise ValidationException(
                    "All substasks must have a unique id", code=404, slug="missing-subtask-unique-id"
                )
            else:
                try:
                    found = subtasks_ids.index(t["id"])
                    raise ValidationException(
                        f'Duplicated subtask id {t["id"]} for the assignment on position {found}',
                        code=404,
                        slug="duplicated-subtask-unique-id",
                    )
                except Exception:
                    subtasks_ids.append(t["id"])

            if not "status" in t:
                raise ValidationException("All substasks must have a status", code=404, slug="missing-subtask-status")
            elif t["status"] not in ["DONE", "PENDING"]:
                raise ValidationException("Subtask status must be DONE or PENDING, received: " + t["status"])

            if not "label" in t:
                raise ValidationException("All substasks must have a label", code=404, slug="missing-task-label")

        item.subtasks = request.data
        item.save()

        return Response(item.subtasks)


class CompletionJobView(APIView):
    @sync_to_async
    def get_task_syllabus(self, task):

        return task.cohort.syllabus_version.syllabus.name

    async def post(self, request, task_id):
        task = await Task.objects.filter(id=task_id).afirst()
        if task is None:
            raise ValidationException("Task not found", code=404, slug="task-not-found")

        asset = await Asset.objects.filter(slug=task.associated_slug).afirst()
        if asset is None:
            raise ValidationException("Asset not found", code=404, slug="asset-not-found")

        syllabus_name = await self.get_task_syllabus(task)

        data = {
            "inputs": {
                "asset_type": task.task_type,
                "title": task.title,
                "syllabus_name": syllabus_name,
                "asset_mardown_body": Asset.decode(asset.readme),
            },
            "include_organization_brief": False,
            "include_purpose_objective": True,
            "execute_async": False,
            "just_format": True,
        }

        async with Service("rigobot", request.user.id, proxy=True) as s:
            return await s.post("/v1/prompting/completion/linked/5/", json=data)


class MeCodeRevisionView(APIView):

    @sync_to_async
    def get_user(self):
        return self.request.user

    @sync_to_async
    def get_github_credentials(self):
        res = None

        if hasattr(self.request.user, "credentialsgithub"):
            res = self.request.user.credentialsgithub

        return res

    @sync_to_async
    def has_github_credentials(self, user):
        return hasattr(user, "credentialsgithub")

    async def get(self, request, task_id=None):
        lang = await aget_user_language(request)
        params = {}
        for key in request.GET.keys():
            params[key] = request.GET.get(key)

        user = await self.get_user()

        if task_id and not (
            task := await Task.objects.filter(id=task_id, user__id=user.id).exclude(github_url=None).afirst()
        ):
            raise ValidationException("Task not found", code=404, slug="task-not-found")

        github_credentials = await self.get_github_credentials()
        if github_credentials is None:
            raise ValidationException(
                translation(
                    lang,
                    en="You need to connect your Github account first",
                    es="Necesitas conectar tu cuenta de Github primero",
                    slug="github-account-not-connected",
                ),
                code=400,
            )

        if task_id and task and task.github_url:
            params["repo"] = task.github_url

        params["github_username"] = github_credentials.username

        async with Service("rigobot", user.id, proxy=True) as s:
            return await s.get("/v1/finetuning/me/coderevision", params=params)

    @consume("add_code_review", consumer=code_revision_service)
    async def post(self, request, task_id):
        lang = await aget_user_language(request)
        params = {}
        for key in request.GET.keys():
            params[key] = request.GET.get(key)

        user = await self.get_user()

        item = await Task.objects.filter(id=task_id, user__id=user.id).afirst()
        if item is None:
            raise ValidationException("Task not found", code=404, slug="task-not-found")

        github_credentials = await self.get_github_credentials()
        if github_credentials is None:
            raise ValidationException(
                translation(
                    lang,
                    en="You need to connect your Github account first",
                    es="Necesitas conectar tu cuenta de Github primero",
                    slug="github-account-not-connected",
                ),
                code=400,
            )

        params["github_username"] = github_credentials.username
        params["repo"] = item.github_url

        async with Service("rigobot", request.user.id, proxy=True) as s:
            return await s.post("/v1/finetuning/coderevision/", data=request.data, params=params)


class AcademyCodeRevisionView(APIView):

    @sync_to_async
    def get_user(self):
        return self.request.user

    @acapable_of("read_assignment")
    async def get(self, request, academy_id=None, task_id=None, coderevision_id=None):
        if task_id and not (
            task := await Task.objects.filter(id=task_id, cohort__academy__id=academy_id)
            .exclude(github_url=None)
            .prefetch_related("user")
            .afirst()
        ):
            raise ValidationException("Task not found", code=404, slug="task-not-found")

        user = await self.get_user()

        params = {}
        for key in request.GET.keys():
            params[key] = request.GET.get(key)

        if task_id and task and task.github_url:
            params["repo"] = task.github_url

        url = "/v1/finetuning/coderevision"

        if coderevision_id is not None:
            url = f"{url}/{coderevision_id}"

        async with Service("rigobot", user.id, proxy=True) as s:
            return await s.get(url, params=params)

    @acapable_of("crud_assignment")
    async def post(self, request, academy_id, task_id=None):
        if task_id and not (
            task := await Task.objects.filter(id=task_id, cohort__academy__id=academy_id)
            .select_related("user")
            .afirst()
        ):
            raise ValidationException("Task not found", code=404, slug="task-not-found")

        user = await self.get_user()

        params = {}
        for key in request.GET.keys():
            params[key] = request.GET.get(key)

        if task_id and task and task.github_url:
            params["repo"] = task.github_url

        async with Service("rigobot", user.id, proxy=True) as s:
            return await s.post("/v1/finetuning/coderevision", data=request.data, params=params)


class AcademyCommitFileView(APIView):

    @acapable_of("read_assignment")
    async def get(self, request, academy_id, task_id=None, commitfile_id=None):
        if task_id and not (task := await Task.objects.filter(id=task_id, cohort__academy__id=academy_id).afirst()):
            raise ValidationException("Task not found", code=404, slug="task-not-found")

        params = {}
        for key in request.GET.keys():
            params[key] = request.GET.get(key)

        if task_id and task and task.github_url:
            params["repo"] = task.github_url

        url = "/v1/finetuning/commitfile"

        if commitfile_id is not None:
            url = f"{url}/{commitfile_id}"

        async with Service("rigobot", proxy=True) as s:
            return await s.get(url, params=params)


class MeCodeRevisionRateView(APIView):

    async def post(self, request, coderevision_id):
        async with Service("rigobot", request.user.id, proxy=True) as s:
            return await s.post(f"/v1/finetuning/rate/coderevision/{coderevision_id}", data=request.data)


class MeCommitFileView(APIView):

    def get(self, request, commitfile_id=None, task_id=None):
        lang = get_user_language(request)
        params = {}
        for key in request.GET.keys():
            params[key] = request.GET.get(key)

        url = "/v1/finetuning/commitfile"
        task = None
        if commitfile_id is not None:
            url = f"{url}/{commitfile_id}"

        elif not (task := Task.objects.filter(id=task_id, user__id=request.user.id).first()):
            raise ValidationException(
                translation(lang, en="Task not found", es="Tarea no encontrada", slug="task-not-found"), code=404
            )

        elif not hasattr(task.user, "credentialsgithub"):
            raise ValidationException(
                translation(
                    lang,
                    en="You need to connect your Github account first",
                    es="Necesitas conectar tu cuenta de Github primero",
                    slug="github-account-not-connected",
                ),
                code=400,
            )

        else:
            params["repo"] = task.github_url
            params["watcher"] = task.user.credentialsgithub.username

        with Service("rigobot", request.user.id, proxy=True) as s:
            return s.get(url, params=params, stream=True)


class FlagView(APIView):
    permission_classes = [IsAuthenticated]

    # POST method for flag generation
    def post(self, request):  # academy_id removed
        asset_seed = request.data.get("asset_seed")
        flag_id = request.data.get("flag_id", None)
        expires_in = request.data.get("expires_in", None)
        lang = get_user_language(request)

        if not asset_seed:
            raise ValidationException(
                translation(
                    lang,
                    en="Asset seed is required",
                    es="La semilla del activo es obligatoria",
                    slug="missing-asset-seed",
                ),
                code=status.HTTP_400_BAD_REQUEST,
                slug="missing-asset-seed",
            )

        try:
            if expires_in is not None:
                expires_in = int(expires_in)
        except ValueError:
            raise ValidationException(
                translation(
                    lang,
                    en="expires_in must be an integer",
                    es="expires_in debe ser un número entero",
                    slug="invalid-expires-in",
                ),
                code=status.HTTP_400_BAD_REQUEST,
                slug="invalid-expires-in",
            )

        try:
            flag_manager = FlagManager()
            new_flag = flag_manager.generate_flag(asset_seed, flag_id=flag_id, expires_in=expires_in)
            return Response({"flag": new_flag}, status=status.HTTP_201_CREATED)
        except ValueError as e:
            eng_message = str(e)
            es_message = eng_message
            if "PRIVATE_FLAG_SEED environment variable is not set" in eng_message:
                es_message = "La variable de entorno PRIVATE_FLAG_SEED no está configurada"
            elif "Asset seed cannot be empty" in eng_message:
                es_message = "La semilla del activo no puede estar vacía"
            raise ValidationException(
                translation(lang, en=eng_message, es=es_message, slug="flag-generation-error"),
                code=status.HTTP_400_BAD_REQUEST,
                slug="flag-generation-error",
            )
        except Exception as e:
            logger.error(f"Error generating flag: {str(e)}")
            raise ValidationException(
                translation(
                    lang,
                    en="An unexpected error occurred while generating the flag",
                    es="Ocurrió un error inesperado al generar el flag",
                    slug="unexpected-flag-generation-error",
                ),
                code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                slug="unexpected-flag-generation-error",
            )

    # GET method for flag validation
    @capable_of("validate_assignment_flag")
    def get(self, request, academy_id):
        submitted_flag = request.query_params.get("flag")
        asset_id = request.query_params.get("asset_id")
        lang = get_user_language(request)

        if not submitted_flag:
            raise ValidationException(
                translation(
                    lang,
                    en="Submitted flag is required",
                    es="El flag enviado es obligatorio",
                    slug="missing-submitted-flag",
                ),
                code=status.HTTP_400_BAD_REQUEST,
                slug="missing-submitted-flag",
            )

        if not asset_id:
            raise ValidationException(
                translation(
                    lang, en="Asset id is required", es="El ID del asset es requerido", slug="missing-asset-id"
                ),
                code=status.HTTP_400_BAD_REQUEST,
                slug="missing-asset-id",
            )

        # Check if an Asset with the given flag_seed exists
        asset = Asset.objects.filter(id=asset_id).first()
        if not asset:
            raise ValidationException(
                translation(
                    lang,
                    en=f"No asset found for the provided id: {asset_id}",
                    es=f"No se encontró ningún asset para el id proporcionado: {asset_id}",
                    slug="asset-not-found-for-id",
                ),
                code=status.HTTP_404_NOT_FOUND,
                slug="asset-not-found-for-id",
            )

        # User had changed revoked_flags_str to be an empty list,
        # so parsing from query_params.get("revoked_flags", "[]") is removed for now.
        # If revoked_flags need to be passed via query param, the parsing logic should be reinstated.
        revoked_flags = []  # Based on user's last change: revoked_flags_str = []

        # If revoked_flags were to be passed as a JSON string in query params:
        # revoked_flags_input_str = request.query_params.get("revoked_flags", "[]")
        # try:
        #     parsed_revoked_flags = json.loads(revoked_flags_input_str)
        #     if not isinstance(parsed_revoked_flags, list):
        #         raise ValidationException(
        #             translation(lang, en="revoked_flags must be a valid JSON list", es="revoked_flags debe ser una lista JSON válida", slug="invalid-revoked-flags-type"),
        #             code=status.HTTP_400_BAD_REQUEST,
        #             slug="invalid-revoked-flags-type"
        #         )
        #     for item in parsed_revoked_flags:
        #         if not isinstance(item, dict) or "flag" not in item or "flag_id" not in item:
        #             raise ValidationException(
        #                 translation(lang, en="Each item in revoked_flags must be a dictionary with 'flag' and 'flag_id' keys", es="Cada elemento en revoked_flags debe ser un diccionario con las claves 'flag' y 'flag_id'", slug="invalid-revoked-flag-item"),
        #                 code=status.HTTP_400_BAD_REQUEST,
        #                 slug="invalid-revoked-flag-item"
        #             )
        #         revoked_flags.append(item)
        # except json.JSONDecodeError:
        #     raise ValidationException(
        #         translation(lang, en="Invalid JSON format for revoked_flags", es="Formato JSON inválido para revoked_flags", slug="invalid-json-revoked-flags"),
        #         code=status.HTTP_400_BAD_REQUEST,
        #         slug="invalid-json-revoked-flags"
        #     )

        try:
            flag_manager = FlagManager()
            is_valid = flag_manager.validate_flag(submitted_flag, asset.flag_seed, revoked_flags=revoked_flags)
            return Response({"is_valid": is_valid}, status=status.HTTP_200_OK)
        except ValueError as e:
            eng_message = str(e)
            es_message = eng_message  # Placeholder
            raise ValidationException(
                translation(lang, en=eng_message, es=es_message, slug="flag-validation-error"),
                code=status.HTTP_400_BAD_REQUEST,
                slug="flag-validation-error",
            )
        except Exception as e:
            logger.error(f"Error validating flag: {str(e)}")
            raise ValidationException(
                translation(
                    lang,
                    en="An unexpected error occurred while validating the flag",
                    es="Ocurrió un error inesperado al validar el flag",
                    slug="unexpected-flag-validation-error",
                ),
                code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                slug="unexpected-flag-validation-error",
            )


class FlagAssetView(APIView):

    # POST method for flag generation
    @capable_of("crud_flag")
    def post(self, request, asset_id):  # academy_id removed

        expires_in = request.data.get("expires_in", None)
        lang = get_user_language(request)

        asset = Asset.objects.filter(id=asset_id).first()
        if not asset:
            raise ValidationException(
                translation(
                    lang,
                    en="Asset not found",
                    es="El asset no fue encontrado",
                    slug="asset-not-found",
                ),
                code=status.HTTP_400_BAD_REQUEST,
                slug="asset-not-found",
            )

        try:
            if expires_in is not None:
                expires_in = int(expires_in)
        except ValueError:
            raise ValidationException(
                translation(
                    lang,
                    en="expires_in must be an integer",
                    es="expires_in debe ser un número entero",
                    slug="invalid-expires-in",
                ),
                code=status.HTTP_400_BAD_REQUEST,
                slug="invalid-expires-in",
            )

        try:
            flag_manager = FlagManager()
            new_flag = flag_manager.generate_flag(asset.flag_seed, expires_in=expires_in)
            return Response({"flag": new_flag}, status=status.HTTP_201_CREATED)
        except ValueError as e:
            eng_message = str(e)
            es_message = eng_message
            if "PRIVATE_FLAG_SEED environment variable is not set" in eng_message:
                es_message = "La variable de entorno PRIVATE_FLAG_SEED no está configurada"
            elif "Asset seed cannot be empty" in eng_message:
                es_message = "La semilla del activo no puede estar vacía"
            raise ValidationException(
                translation(lang, en=eng_message, es=es_message, slug="flag-generation-error"),
                code=status.HTTP_400_BAD_REQUEST,
                slug="flag-generation-error",
            )
        except Exception as e:
            logger.error(f"Error generating flag: {str(e)}")
            raise ValidationException(
                translation(
                    lang,
                    en="An unexpected error occurred while generating the flag",
                    es="Ocurrió un error inesperado al generar el flag",
                    slug="unexpected-flag-generation-error",
                ),
                code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                slug="unexpected-flag-generation-error",
            )
