from breathecode.authenticate.models import ProfileAcademy
import logging
from django.shortcuts import render
from django.db.models import Q
from rest_framework.views import APIView
from django.contrib.auth.models import AnonymousUser
from breathecode.utils import localize_query, ValidationException
from breathecode.admissions.models import CohortUser, Cohort
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from breathecode.utils import APIException
from .models import Task
from .serializers import TaskGETSerializer, PUTTaskSerializer, PostTaskSerializer
from .actions import sync_cohort_tasks

logger = logging.getLogger(__name__)


class TaskTeacherView(APIView):
    def get(self, request):

        items = Task.objects.all()
        logger.debug(f"Found {items.count()} tasks")

        if request.user is not None:
            profile_ids = ProfileAcademy.objects.filter(
                user=request.user.id).values_list('academy__id', flat=True)
            if profile_ids is None:
                raise APIException(
                    "The quest user must belong to at least one academy to be able to request student tasks"
                )
            items = items.filter(
                Q(cohort__academy__id__in=profile_ids)
                | Q(cohort__isnull=True))
            print(items)

        academy = request.GET.get('academy', None)
        if academy is not None:
            items = items.filter(
                Q(cohort__academy__slug__in=academy.split(","))
                | Q(cohort__isnull=True))

        user = request.GET.get('user', None)
        if user is not None:
            items = items.filter(user__id__in=user.split(","))

        # tasks these cohorts (not the users, but the tasts belong to the cohort)
        cohort = request.GET.get('cohort', None)
        if cohort is not None:
            items = items.filter(
                Q(cohort__slug__in=cohort.split(","))
                | Q(cohort__id__in=cohort.split(",")))

        # tasks from users that belong to these cohort
        stu_cohort = request.GET.get('stu_cohort', None)
        if stu_cohort is not None:
            items = items.filter(
                user__cohortuser__cohort__id__in=stu_cohort.split(","),
                user__cohortuser__role="STUDENT")

        # tasks from users that belong to these cohort
        teacher = request.GET.get('teacher', None)
        if teacher is not None:
            teacher_cohorts = CohortUser.objects.filter(
                user__id__in=teacher.split(","),
                role="TEACHER").values_list('cohort__id', flat=True)
            items = items.filter(
                user__cohortuser__cohort__id__in=teacher_cohorts,
                user__cohortuser__role="STUDENT")

        task_status = request.GET.get('task_status', None)
        if task_status is not None:
            items = items.filter(task_status__in=task_status.split(","))

        revision_status = request.GET.get('revision_status', None)
        if revision_status is not None:
            items = items.filter(
                revision_status__in=revision_status.split(","))

        task_type = request.GET.get('task_type', None)
        if task_type is not None:
            items = items.filter(task_type__in=task_type.split(","))

        items = items.order_by('created_at')
        serializer = TaskGETSerializer(items, many=True)
        return Response(serializer.data)


@api_view(['POST'])
def sync_cohort_tasks_view(request, cohort_id=None):
    item = Cohort.objects.filter(id=cohort_id).first()
    if item is None:
        raise ValidationException("Cohort not found")

    syncronized = sync_cohort_tasks(item)
    if len(syncronized) == 0:
        raise ValidationException("No tasks updated")

    serializer = TaskGETSerializer(syncronized, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


class TaskMeView(APIView):
    """
    List all snippets, or create a new snippet.
    """
    def get(self, request, task_id=None, user_id=None):

        if task_id is not None:
            item = Task.objects.filter(id=task_id).first()
            if item is None:
                raise ValidationException("Task not found")

            serializer = TaskGETSerializer(item, many=False)
            return Response(serializer.data)

        user_id = request.user.id
        tasks = Task.objects.filter(user__id=user_id)
        serializer = TaskGETSerializer(tasks, many=True)
        return Response(serializer.data)

    def put(self, request, task_id):

        item = Task.objects.filter(id=task_id).first()
        if item is None:
            raise ValidationException("Task not found")

        serializer = PUTTaskSerializer(item,
                                       data=request.data,
                                       context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, user_id=None):

        # only create tasks for yourself
        if user_id is None:
            user_id = request.user.id

        payload = request.data

        if isinstance(request.data, list) == False:
            payload = [request.data]

        serializer = PostTaskSerializer(data=payload,
                                        context={
                                            "request": request,
                                            "user_id": user_id
                                        },
                                        many=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
