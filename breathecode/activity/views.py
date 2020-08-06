from django.shortcuts import render
from django.utils import timezone
from .utils import resolve_google_credentials, check_params
from .serializers import ActivitySerializer
from rest_framework.response import Response
from rest_framework.views import APIView
from google.cloud import datastore
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

        resolve_google_credentials()
        client = datastore.Client()
        query = client.query(kind='nps_answer')
        query_iter = query.fetch()
        
        return Response(query_iter)

    def post(self, request, format=None):
        resolve_google_credentials()

        answer_dict=request.data

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