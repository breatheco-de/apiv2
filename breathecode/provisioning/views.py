import re
from django.shortcuts import render
from django.utils import timezone
from django.db.models import Avg
from django.http import HttpResponse
from breathecode.admissions.models import CohortUser, Academy
from .caches import AnswerCache
from breathecode.utils.api_view_extensions.api_view_extensions import APIViewExtensions
from .models import Answer, Survey, ReviewPlatform, Review
from .tasks import generate_user_cohort_survey_answers
from rest_framework import serializers
from rest_framework.exceptions import ValidationError, NotFound
from rest_framework.permissions import AllowAny, IsAuthenticated
from .serializers import (AnswerPUTSerializer, AnswerSerializer, SurveySerializer, SurveyPUTSerializer,
                          BigAnswerSerializer, SurveySmallSerializer, ReviewPlatformSerializer,
                          ReviewSmallSerializer, ReviewPUTSerializer)
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.views import APIView
from rest_framework import status
from breathecode.utils import capable_of, ValidationException, HeaderLimitOffsetPagination, GenerateLookupsMixin
from PIL import Image
from django.db.models import Q
from breathecode.utils.find_by_full_name import query_like_by_full_name
from django.db.models import QuerySet
from .utils import strings


class ContainerView(APIView):
    """
    List all snippets, or create a new snippet.
    """

    @has_permission('get_containers')
    def get(self, request, format=None, academy_id=None):

        academy = Academy.objects.get(id=academy_id)
        items = Review.objects.filter(cohort__academy__id=academy.id)
        lookup = {}

        start = request.GET.get('start', None)
        if start is not None:
            start_date = datetime.datetime.strptime(start, '%Y-%m-%d').date()
            lookup['created_at__gte'] = start_date

        end = request.GET.get('end', None)
        if end is not None:
            end_date = datetime.datetime.strptime(end, '%Y-%m-%d').date()
            lookup['created_at__lte'] = end_date

        if 'status' in self.request.GET:
            param = self.request.GET.get('status')
            lookup['status'] = param

        if 'platform' in self.request.GET:
            param = self.request.GET.get('platform')
            items = items.filter(platform__name__icontains=param)

        if 'cohort' in self.request.GET:
            param = self.request.GET.get('cohort')
            lookup['cohort__id'] = param

        if 'author' in self.request.GET:
            param = self.request.GET.get('author')
            lookup['author__id'] = param

        sort_by = '-created_at'
        if 'sort' in self.request.GET and self.request.GET['sort'] != '':
            sort_by = self.request.GET.get('sort')

        items = items.filter(**lookup).order_by(sort_by)

        like = request.GET.get('like', None)
        if like is not None:
            items = query_like_by_full_name(like=like, items=items, prefix='author__')

        page = self.paginate_queryset(items, request)
        serializer = ReviewSmallSerializer(page, many=True)

        if self.is_paginate(request):
            return self.get_paginated_response(serializer.data)
        else:
            return Response(serializer.data, status=200)

    @capable_of('crud_review')
    def put(self, request, review_id, academy_id=None):

        review = Review.objects.filter(id=review_id, cohort__academy__id=academy_id).first()
        if review is None:
            raise NotFound('This review does not exist on this academy')

        serializer = ReviewPUTSerializer(review,
                                         data=request.data,
                                         context={
                                             'request': request,
                                             'review': review_id,
                                             'academy_id': academy_id
                                         })
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of('crud_review')
    def delete(self, request, academy_id=None):
        # TODO: here i don't add one single delete, because i don't know if it is required
        lookups = self.generate_lookups(request, many_fields=['id'])
        # automation_objects

        if not lookups:
            raise ValidationException('Missing parameters in the querystring', code=400)

        items = Review.objects.filter(**lookups, academy__id=academy_id)

        for item in items:
            item.status = 'IGNORE'
            item.save()

        return Response(None, status=status.HTTP_204_NO_CONTENT)
