from .utils import resolve_google_credentials, check_params
from rest_framework.response import Response
from rest_framework.views import APIView
from google.cloud import datastore
from rest_framework import status
from django.db.models import Q
from breathecode.admissions.models import Cohort
from breathecode.utils import capable_of, ValidationException
from breathecode.services.google_cloud.datastore import Datastore
from breathecode.services.google_cloud import Datastore
# Create your views here.

# DOCUMENTATION RESOURCES
# https://www.programcreek.com/python/example/88825/google.cloud.datastore.Entity
# https://cloud.google.com/datastore/docs/concepts/entities
# https://googleapis.dev/python/datastore/latest/index.html


class ActivityView(APIView):
    """
    List all snippets, or create a new snippet.
    """

    def get(self, request, format=None):
        # datastore = Datastore()
        # return datastore.fetch(kind='nps_answer')

        resolve_google_credentials()
        client = datastore.Client()
        query = client.query(kind='nps_answer')
        query_iter = query.fetch()

        return Response(query_iter)

    def post(self, request, format=None):
        resolve_google_credentials()

        answer_dict = request.data

        check_params(answer_dict, 'comment', 'score', 'user_id')

        client = datastore.Client()
        entity = datastore.Entity(client.key('nps_answer'))
        entity.update({
            'comment': 'Personal',
            'score': False,
            'user_id': 4,
            'certificate': answer_dict['certificate'] if 'certificate' in answer_dict else None,
            'academy': answer_dict['academy'] if 'academy' in answer_dict else None,
            'cohort': answer_dict['cohort'] if 'cohort' in answer_dict else None,
            'mentor': answer_dict['mentor'] if 'mentor' in answer_dict else None
        })
        client.put(entity)

        return Response(answer_dict, status=status.HTTP_201_CREATED)

        # answer_dict=request.data
        # check_params(answer_dict, 'comment', 'score', 'user_id')

        # datastore = Datastore()
        # datastore.update('nps_answer', {
        #     'comment': 'Personal',
        #     'score': False,
        #     'user_id': 4,
        #     'certificate': answer_dict['certificate'] if 'certificate' in answer_dict else None,
        #     'academy': answer_dict['academy'] if 'academy' in answer_dict else None,
        #     'cohort': answer_dict['cohort'] if 'cohort' in answer_dict else None,
        #     'mentor': answer_dict['mentor'] if 'mentor' in answer_dict else None
        # })

        # return Response(answer_dict, status=status.HTTP_201_CREATED)


class CohortActivityView(APIView):
    """
    List all snippets, or create a new snippet.
    """

    @capable_of('read_cohort_activity')
    def get(self, request, cohort_slug=None, academy_id=None, format=None):

        cohort = Cohort.objects.filter(
            Q(slug=cohort_slug) | Q(id=cohort_slug)).first()
        if cohort is None:
            raise ValidationException("Cohort slug or id not found")

        datastore = Datastore()
        query_iter = datastore.fetch(kind='student_activity')

        return Response(query_iter)

    def post(self, request, format=None):
        resolve_google_credentials()

        answer_dict = request.data

        check_params(answer_dict, 'comment', 'score', 'user_id')

        client = datastore.Client()
        entity = datastore.Entity(client.key('nps_answer'))
        entity.update({
            'comment': 'Personal',
            'score': False,
            'user_id': 4,
            'certificate': answer_dict['certificate'] if 'certificate' in answer_dict else None,
            'academy': answer_dict['academy'] if 'academy' in answer_dict else None,
            'cohort': answer_dict['cohort'] if 'cohort' in answer_dict else None,
            'mentor': answer_dict['mentor'] if 'mentor' in answer_dict else None
        })
        client.put(entity)

        return Response(answer_dict, status=status.HTTP_201_CREATED)

        # answer_dict=request.data
        # check_params(answer_dict, 'comment', 'score', 'user_id')

        # datastore = Datastore()
        # datastore.update('nps_answer', {
        #     'comment': 'Personal',
        #     'score': False,
        #     'user_id': 4,
        #     'certificate': answer_dict['certificate'] if 'certificate' in answer_dict else None,
        #     'academy': answer_dict['academy'] if 'academy' in answer_dict else None,
        #     'cohort': answer_dict['cohort'] if 'cohort' in answer_dict else None,
        #     'mentor': answer_dict['mentor'] if 'mentor' in answer_dict else None
        # })

        # return Response(answer_dict, status=status.HTTP_201_CREATED)
