from django.shortcuts import render
from django.utils import timezone
from django.http import HttpResponse
from breathecode.admissions.models import CohortUser, Academy
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


@api_view(['GET'])
@permission_classes([AllowAny])
def track_survey_open(request, answer_id=None):

    item = None
    if answer_id is not None:
        item = Answer.objects.filter(id=answer_id, status='SENT').first()

    if item is not None:
        item.status = 'OPENED'
        item.opened_at = timezone.now()
        item.save()

    image = Image.new('RGB', (1, 1))
    response = HttpResponse(content_type='image/png')
    image.save(response, 'PNG')
    return response


@api_view(['GET'])
def get_survey_questions(request, survey_id=None):

    survey = Survey.objects.filter(id=survey_id).first()
    if survey is None:
        raise ValidationException('Survey not found', 404)

    utc_now = timezone.now()
    if utc_now > survey.sent_at + survey.duration:
        raise ValidationException('This survey has already expired', 400)

    cu = CohortUser.objects.filter(cohort=survey.cohort, role='STUDENT', user=request.user).first()
    if cu is None:
        raise ValidationException('This student does not belong to this cohort', 400)

    cohort_teacher = CohortUser.objects.filter(cohort=survey.cohort, role='TEACHER')
    if cohort_teacher.count() == 0:
        raise ValidationException('This cohort must have a teacher assigned to be able to survey it', 400)

    answers = generate_user_cohort_survey_answers(request.user, survey, status='OPENED')
    serializer = AnswerSerializer(answers, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


# Create your views here.
class GetAnswerView(APIView):
    """
    List all snippets, or create a new snippet.
    """

    extensions = APIViewExtensions(sort='-created_at', paginate=True)

    @capable_of('read_nps_answers')
    def get(self, request, format=None, academy_id=None):
        handler = self.extensions(request)

        items = Answer.objects.filter(academy__id=academy_id)
        lookup = {}

        users = request.GET.get('user', None)
        if users is not None and users != '':
            items = items.filter(user__id__in=users.split(','))

        cohorts = request.GET.get('cohort', None)
        if cohorts is not None and cohorts != '':
            items = items.filter(cohort__slug__in=cohorts.split(','))

        mentors = request.GET.get('mentor', None)
        if mentors is not None and mentors != '':
            items = items.filter(mentor__id__in=mentors.split(','))

        events = request.GET.get('event', None)
        if events is not None and events != '':
            items = items.filter(event__id__in=events.split(','))

        score = request.GET.get('score', None)
        if score is not None and score != '':
            lookup['score'] = score

        _status = request.GET.get('status', None)
        if _status is not None and _status != '':
            items = items.filter(status__in=_status.split(','))

        surveys = request.GET.get('survey', None)
        if surveys is not None and surveys != '':
            items = items.filter(survey__id__in=surveys.split(','))

        items = items.filter(**lookup)

        like = request.GET.get('like', None)
        if like is not None:
            items = query_like_by_full_name(like=like, items=items, prefix='user__')

        items = handler.queryset(items)
        serializer = AnswerSerializer(items, many=True)

        return handler.response(serializer.data)


class AnswerMeView(APIView):
    """
    Student answers a survey (normally several answers are required for each survey)
    """
    def put(self, request, answer_id=None):
        if answer_id is None:
            raise ValidationException('Missing answer_id', slug='missing-answer-id')

        answer = Answer.objects.filter(user=request.user, id=answer_id).first()
        if answer is None:
            raise ValidationException('This survey does not exist for this user',
                                      code=404,
                                      slug='answer-of-other-user-or-not-exists')

        serializer = AnswerPUTSerializer(answer,
                                         data=request.data,
                                         context={
                                             'request': request,
                                             'answer': answer_id
                                         })
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, answer_id=None):
        if answer_id is None:
            raise ValidationException('Missing answer_id', slug='missing-answer-id')

        answer = Answer.objects.filter(user=request.user, id=answer_id).first()
        if answer is None:
            raise ValidationException('This survey does not exist for this user',
                                      code=404,
                                      slug='answer-of-other-user-or-not-exists')

        serializer = BigAnswerSerializer(answer)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AcademyAnswerView(APIView):
    @capable_of('read_nps_answers')
    def get(self, request, academy_id=None, answer_id=None):
        if answer_id is None:
            raise ValidationException('Missing answer_id', code=404)

        answer = Answer.objects.filter(academy__id=academy_id, id=answer_id).first()
        if answer is None:
            raise ValidationException('This survey does not exist for this academy')

        serializer = BigAnswerSerializer(answer)
        return Response(serializer.data, status=status.HTTP_200_OK)


class SurveyView(APIView, HeaderLimitOffsetPagination, GenerateLookupsMixin):
    """
    List all snippets, or create a new snippet.
    """
    @capable_of('crud_survey')
    def post(self, request, academy_id=None):

        serializer = SurveySerializer(data=request.data,
                                      context={
                                          'request': request,
                                          'academy_id': academy_id
                                      })
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    """
    List all snippets, or create a new snippet.
    """

    @capable_of('crud_survey')
    def put(self, request, survey_id=None, academy_id=None):
        if survey_id is None:
            raise ValidationException('Missing survey_id')

        survey = Survey.objects.filter(id=survey_id).first()
        if survey is None:
            raise NotFound('This survey does not exist')

        serializer = SurveyPUTSerializer(survey,
                                         data=request.data,
                                         context={
                                             'request': request,
                                             'survey': survey_id,
                                             'academy_id': academy_id
                                         })
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of('read_survey')
    def get(self, request, survey_id=None, academy_id=None):

        if survey_id is not None:
            survey = Survey.objects.filter(id=survey_id).first()
            if survey is None:
                raise NotFound('This survey does not exist')

            serializer = SurveySerializer(survey)
            return Response(serializer.data, status=status.HTTP_200_OK)

        items = Survey.objects.filter(cohort__academy__id=academy_id)
        lookup = {}

        if 'status' in self.request.GET:
            param = self.request.GET.get('status')
            lookup['status'] = param

        if 'cohort' in self.request.GET:
            param = self.request.GET.get('cohort')
            lookup['cohort__slug'] = param

        if 'lang' in self.request.GET:
            param = self.request.GET.get('lang')
            lookup['lang'] = param

        items = items.filter(**lookup).order_by('status', '-created_at')

        page = self.paginate_queryset(items, request)
        serializer = SurveySmallSerializer(page, many=True)

        if self.is_paginate(request):
            return self.get_paginated_response(serializer.data)
        else:
            return Response(serializer.data, status=status.HTTP_200_OK)

    @capable_of('crud_survey')
    def delete(self, request, academy_id=None, survey_id=None):

        lookups = self.generate_lookups(request, many_fields=['id'])

        if lookups and survey_id:
            raise ValidationException(
                'survey_id was provided in url '
                'in bulk mode request, use querystring style instead',
                code=400,
                slug='survey-id-and-lookups-together')

        if not lookups and not survey_id:
            raise ValidationException('survey_id was not provided in url',
                                      code=400,
                                      slug='without-survey-id-and-lookups')

        if lookups:
            items = Survey.objects.filter(**lookups, cohort__academy__id=academy_id).exclude(status='SENT')

            ids = [item.id for item in items]

            if answers := Answer.objects.filter(survey__id__in=ids, status='ANSWERED'):

                slugs = set([answer.survey.cohort.slug for answer in answers])

                raise ValidationException(
                    f'Survey cannot be deleted because it has been answered for cohorts {", ".join(slugs)}',
                    code=400,
                    slug='survey-cannot-be-deleted')

            for item in items:
                item.delete()

            return Response(None, status=status.HTTP_204_NO_CONTENT)

        sur = Survey.objects.filter(id=survey_id,
                                    cohort__academy__id=academy_id).exclude(status='SENT').first()
        if sur is None:
            raise ValidationException('Survey not found', 404, slug='survey-not-found')

        if Answer.objects.filter(survey__id=survey_id, status='ANSWERED'):
            raise ValidationException('Survey cannot be deleted', code=400, slug='survey-cannot-be-deleted')

        sur.delete()
        return Response(None, status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_review_platform(request, platform_slug=None):

    rp = ReviewPlatform.objects.all()
    if platform_slug is not None:
        rp = cu.filter(slug=platform_slug).first()
        if rp is not None:
            serializer = ReviewPlatformSerializer(items, many=False)
            return Response(serializer.data)
        else:
            raise ValidationException('Review platform not found', slug='reivew_platform_not_found', code=404)
    else:
        serializer = ReviewPlatformSerializer(rp, many=True)
        return Response(serializer.data)


class ReviewView(APIView, HeaderLimitOffsetPagination, GenerateLookupsMixin):
    """
    List all snippets, or create a new snippet.
    """
    @capable_of('read_review')
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
