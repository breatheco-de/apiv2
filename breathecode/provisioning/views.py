import re
from django.shortcuts import render
from django.utils import timezone
from django.db.models import Avg
from django.http import HttpResponse
from breathecode.admissions.models import CohortUser, Academy
from breathecode.utils.api_view_extensions.api_view_extensions import APIViewExtensions
from .models import Answer, Survey, ReviewPlatform, Review
# from .tasks import generate_user_cohort_survey_answers
from rest_framework import serializers
from .serializers import (ContainerMeSmallSerializer, ContainerMeBigSerializer)
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.views import APIView
from rest_framework import status
from breathecode.utils import capable_of, ValidationException, HeaderLimitOffsetPagination, GenerateLookupsMixin
from django.db.models import Q
from django.db.models import QuerySet


class ContainerView(APIView):
    """
    List all snippets, or create a new snippet.
    """

    @has_permission('get_containers')
    def get(self, request, format=None, container_id=None):

        # if container_id

        containers = ProvisioningContainer.objects.filter(user=request.user)
        lookup = {}

        assignment = request.GET.get('assignment', None)
        if assignment is not None:
            lookup['task_associated_slug'] = assignment

        like = request.GET.get('like', None)
        if like is not None:
            items = items.filter(display_name__icontains=like)

        sort_by = '-created_at'
        if 'sort' in self.request.GET and self.request.GET['sort'] != '':
            sort_by = self.request.GET.get('sort')

        items = items.filter(**lookup).order_by(sort_by)

        page = self.paginate_queryset(items, request)
        serializer = ContainerMeSmallSerializer(page, many=True)

        if self.is_paginate(request):
            return self.get_paginated_response(serializer.data)
        else:
            return Response(serializer.data, status=200)

    @has_permission('create_container')
    def post(self, request):

        lang = get_user_language(request)
        review = ProvisioningContainer.objects.filter(id=review_id, cohort__academy__id=academy_id).first()
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
