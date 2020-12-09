from django.shortcuts import render
from .models import Task
from django.db.models import Q
from rest_framework.views import APIView
from django.contrib.auth.models import AnonymousUser
from breathecode.utils import localize_query
from breathecode.admissions.models import CohortUser
from rest_framework.decorators import api_view, permission_classes
from .serializers import PostTaskSerializer, TaskGETSerializer, PUTTaskSerializer
from rest_framework.response import Response
from rest_framework import status

@api_view(['GET'])
def get_tasks(request, id=None):


    items = Task.objects.all()

    if isinstance(request.user, AnonymousUser) == False:
        # filter only to the local academy
        items = localize_query(items, request, "cohort__academy__id__in")

    academy = request.GET.get('academy', None)
    if academy is not None:
        items = items.filter(cohort__academy__slug__in=academy.split(","))

    user = request.GET.get('user', None)
    if user is not None:
        items = items.filter(user__in=user.split(","))

    # tasks these cohorts (not the users, but the tasts belong to the cohort)
    cohort = request.GET.get('cohort', None)
    if cohort is not None:
        items = items.filter(Q(cohort__slug__in=cohort.split(",")) | Q(cohort__id__in=cohort.split(",")))

    # tasks from users that belong to these cohort
    stu_cohort = request.GET.get('stu_cohort', None)
    if stu_cohort is not None:
        items = items.filter(user__cohortuser__cohort__id__in=stu_cohort.split(","), user__cohortuser__role="STUDENT")

    # tasks from users that belong to these cohort
    teacher = request.GET.get('teacher', None)
    if teacher is not None:
        teacher_cohorts = CohortUser.objects.filter(user__id__in=teacher.split(","), role="TEACHER").values_list('cohort__id', flat=True)
        print(teacher_cohorts)
        items = items.filter(user__cohortuser__cohort__id__in=teacher_cohorts, user__cohortuser__role="STUDENT")

    task_status = request.GET.get('task_status', None)
    if task_status is not None:
        items = items.filter(task_status__in=task_status.split(","))

    revision_status = request.GET.get('revision_status', None)
    if revision_status is not None:
        items = items.filter(revision_status__in=revision_status.split(","))

    task_type = request.GET.get('task_type', None)
    if task_type is not None:
        items = items.filter(task_type__in=task_type.split(","))

    items = items.order_by('created_at')
    serializer = TaskGETSerializer(items, many=True)
    return Response(serializer.data)

class TaskView(APIView):
    """
    List all snippets, or create a new snippet.
    """
    def get(self, request, task_id=None, user_id=None):

        if task_id is not None:
            item = Task.objects.filter(id=task_id).first()
            if item is None:
                raise serializers.ValidationError("Task not found", code=404)

            serializer = SmallTaskSerializer(item, many=False)
            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_404_NOT_FOUND)

    def put(self, request, task_id):
        item = Task.objects.filter(id=task_id).first()
        if item is None:
            raise serializers.ValidationError("Task not found", code=404)
        
        serializer = PUTTaskSerializer(item, data=request.data, context={ "request": request })
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, user_id=None):

        if user_id is None:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer = PostTaskSerializer(data=request.data, context={ "request": request, "user_id": user_id })
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)