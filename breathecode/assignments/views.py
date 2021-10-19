from breathecode.authenticate.models import ProfileAcademy
import logging
from django.shortcuts import render
from django.utils import timezone
from django.db.models import Q
from rest_framework.views import APIView
from django.contrib.auth.models import AnonymousUser
from django.contrib import messages
from breathecode.utils import ValidationException, capable_of, localize_query
from breathecode.admissions.models import CohortUser, Cohort
from breathecode.authenticate.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from breathecode.utils import APIException
from .models import Task
from .actions import deliver_task
from .forms import DeliverAssigntmentForm
from .serializers import (TaskGETSerializer, PUTTaskSerializer, PostTaskSerializer, TaskGETDeliverSerializer)
from .actions import sync_cohort_tasks

logger = logging.getLogger(__name__)


class TaskTeacherView(APIView):
    def get(self, request):

        items = Task.objects.all()
        logger.debug(f'Found {items.count()} tasks')

        if request.user is not None:
            profile_ids = ProfileAcademy.objects.filter(user=request.user.id).values_list('academy__id',
                                                                                          flat=True)
            if profile_ids is None:
                raise APIException(
                    'The quest user must belong to at least one academy to be able to request student tasks')
            items = items.filter(Q(cohort__academy__id__in=profile_ids) | Q(cohort__isnull=True))

        academy = request.GET.get('academy', None)
        if academy is not None:
            items = items.filter(Q(cohort__academy__slug__in=academy.split(',')) | Q(cohort__isnull=True))

        user = request.GET.get('user', None)
        if user is not None:
            items = items.filter(user__id__in=user.split(','))

        # tasks these cohorts (not the users, but the tasts belong to the cohort)
        cohort = request.GET.get('cohort', None)
        if cohort is not None:
            items = items.filter(Q(cohort__slug__in=cohort.split(',')) | Q(cohort__id__in=cohort.split(',')))

        # tasks from users that belong to these cohort
        stu_cohort = request.GET.get('stu_cohort', None)
        if stu_cohort is not None:
            ids = stu_cohort.split(',')
            if ids[0].isnumeric():
                items = items.filter(user__cohortuser__cohort__id__in=ids, user__cohortuser__role='STUDENT')
            else:
                items = items.filter(user__cohortuser__cohort__slug__in=ids, user__cohortuser__role='STUDENT')

        # tasks from users that belong to these cohort
        teacher = request.GET.get('teacher', None)
        if teacher is not None:
            teacher_cohorts = CohortUser.objects.filter(user__id__in=teacher.split(','),
                                                        role='TEACHER').values_list('cohort__id', flat=True)
            items = items.filter(user__cohortuser__cohort__id__in=teacher_cohorts,
                                 user__cohortuser__role='STUDENT')

        task_status = request.GET.get('task_status', None)
        if task_status is not None:
            items = items.filter(task_status__in=task_status.split(','))

        revision_status = request.GET.get('revision_status', None)
        if revision_status is not None:
            items = items.filter(revision_status__in=revision_status.split(','))

        task_type = request.GET.get('task_type', None)
        if task_type is not None:
            items = items.filter(task_type__in=task_type.split(','))

        items = items.order_by('created_at')
        serializer = TaskGETSerializer(items, many=True)
        return Response(serializer.data)


@api_view(['POST'])
def sync_cohort_tasks_view(request, cohort_id=None):
    item = Cohort.objects.filter(id=cohort_id).first()
    if item is None:
        raise ValidationException('Cohort not found')

    syncronized = sync_cohort_tasks(item)
    if len(syncronized) == 0:
        raise ValidationException('No tasks updated')

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
                raise ValidationException('Task not found')

            serializer = TaskGETSerializer(item, many=False)
            return Response(serializer.data)

        user_id = request.user.id
        tasks = Task.objects.filter(user__id=user_id)
        serializer = TaskGETSerializer(tasks, many=True)
        return Response(serializer.data)

    def put(self, request, task_id):

        item = Task.objects.filter(id=task_id).first()
        if item is None:
            raise ValidationException('Task not found')

        serializer = PUTTaskSerializer(item, data=request.data, context={'request': request})
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
                                            'request': request,
                                            'user_id': user_id
                                        },
                                        many=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TaskMeDeliverView(APIView):
    """
    List all snippets, or create a new snippet.
    """
    @capable_of('task_advanced_details')
    def get(self, request, task_id, academy_id):

        item = Task.objects.filter(id=task_id).first()
        if item is None:
            raise ValidationException('Task not found')

        serializer = TaskGETDeliverSerializer(item, many=False)
        return Response(serializer.data)


def deliver_assignment_view(request, task_id, token):

    if request.method == 'POST':
        _dict = request.POST.copy()
        form = DeliverAssigntmentForm(_dict)

        if 'github_url' not in _dict or _dict['github_url'] == '':
            messages.error(request, 'Github URL is required')
            return render(request, 'form.html', {'form': form})

        token = Token.objects.filter(key=_dict['token']).first()
        if token is None or token.expires_at < timezone.now():
            messages.error(request, f'Invalid or expired deliver token {_dict["token"]}')
            return render(request, 'form.html', {'form': form})

        task = Task.objects.filter(id=_dict['task_id']).first()
        if task is None:
            messages.error(request, 'Invalid task id')
            return render(request, 'form.html', {'form': form})

        deliver_task(
            task=task,
            github_url=_dict['github_url'],
            live_url=_dict['live_url'],
        )

        if 'callback' in _dict and _dict['callback'] != '':
            return HttpResponseRedirect(redirect_to=_dict['callback'] + '?msg=The task has been delivered')
        else:
            return render(request, 'message.html', {'message': 'The task has been delivered'})
    else:
        task = Task.objects.filter(id=task_id).first()
        if task is None:
            return render(request, 'message.html', {
                'message': f'Invalid assignment id {str(task_id)}',
            })

        _dict = request.GET.copy()
        _dict['callback'] = request.GET.get('callback', '')
        _dict['token'] = token
        _dict['task_name'] = task.title
        _dict['task_id'] = task.id
        form = DeliverAssigntmentForm(_dict)
    return render(
        request,
        'form.html',
        {
            'form': form,
            # 'heading': 'Deliver project assignment',
            'intro': 'Please fill the following information to deliver your assignment',
            'btn_lable': 'Deliver Assignment'
        })
