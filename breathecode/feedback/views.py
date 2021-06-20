from django.shortcuts import render
from django.utils import timezone
from django.http import HttpResponse
from breathecode.admissions.models import CohortUser
from .models import Answer, Survey
from .tasks import generate_user_cohort_survey_answers
from rest_framework import serializers
from rest_framework.exceptions import ValidationError, NotFound
from rest_framework.permissions import AllowAny, IsAuthenticated
from .serializers import (
    AnswerPUTSerializer, AnswerSerializer, SurveySerializer, SurveyPUTSerializer, BigAnswerSerializer
)
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.views import APIView
from rest_framework import status
from breathecode.utils import capable_of, ValidationException, HeaderLimitOffsetPagination
from PIL import Image
from django.db.models import Q

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
    response = HttpResponse(content_type="image/png")
    image.save(response, "PNG")
    return response

@api_view(['GET'])
def get_survey_questions(request, survey_id=None):

    survey = Survey.objects.filter(id=survey_id).first()
    if survey is None:
        raise ValidationException("Survey not found", 404)

    utc_now = timezone.now()
    if utc_now > survey.created_at + survey.duration:
        raise ValidationException("This survey has already expired", 400)

    cu = CohortUser.objects.filter(cohort=survey.cohort, role="STUDENT", user=request.user).first()
    if cu is None:
        raise ValidationException("This student does not belong to this cohort", 400)

    cohort_teacher = CohortUser.objects.filter(cohort=survey.cohort, role="TEACHER")
    if cohort_teacher.count() == 0:
        raise ValidationException("This cohort must have a teacher assigned to be able to survey it", 400)

    answers = generate_user_cohort_survey_answers(request.user, survey, status='OPENED')
    serializer = AnswerSerializer(answers, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

# Create your views here.
class GetAnswerView(APIView, HeaderLimitOffsetPagination):
    """
    List all snippets, or create a new snippet.
    """
    @capable_of('read_nps_answers')
    def get(self, request, format=None, academy_id=None):

        items = Answer.objects.filter(academy__id=academy_id)
        lookup = {}

        if 'user' in self.request.GET:
            param = self.request.GET.get('user')
            lookup['user__id'] = param

        if 'cohort' in self.request.GET:
            param = self.request.GET.get('cohort')
            lookup['cohort__slug'] = param

        if 'mentor' in self.request.GET:
            param = self.request.GET.get('mentor')
            lookup['mentor__id'] = param

        if 'event' in self.request.GET:
            param = self.request.GET.get('event')
            lookup['event__id'] = param

        if 'score' in self.request.GET:
            param = self.request.GET.get('score')
            lookup['score'] = param

        if 'status' in self.request.GET:
            param = self.request.GET.get('status')
            lookup['status'] = param

        items = items.filter(**lookup).order_by('-created_at')

        like = request.GET.get('like', None)
        if like is not None:            
            for query in like.split():
                items = items.filter(Q(user__first_name__icontains=query) |
                    Q(user__last_name__icontains=query) | Q(user__email__icontains=query))

        page = self.paginate_queryset(items, request)
        serializer = AnswerSerializer(page, many=True)

        if self.is_paginate(request):
            return self.get_paginated_response(serializer.data)
        else:
            return Response(serializer.data, status=status.HTTP_200_OK)



class AnswerMeView(APIView):
    """
    List all snippets, or create a new snippet.
    """
    def put(self, request, answer_id=None):
        if answer_id is None:
            raise serializers.ValidationError("Missing answer_id", code=400)

        answer = Answer.objects.filter(user=request.user,id=answer_id).first()
        if answer is None:
            raise NotFound('This survey does not exist for this user')

        serializer = AnswerPUTSerializer(answer, data=request.data, context={ "request": request, "answer": answer_id })
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, answer_id=None):
        if answer_id is None:
            raise serializers.ValidationError("Missing answer_id", code=404)

        answer = Answer.objects.filter(user=request.user,id=answer_id).first()
        if answer is None:
            raise NotFound('This survey does not exist for this user')

        serializer = BigAnswerSerializer(answer)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AcademyAnswerView(APIView):

    @capable_of('read_nps_answers')
    def get(self, request, academy_id=None, answer_id=None):
        if answer_id is None:
            raise ValidationException("Missing answer_id", code=404)

        answer = Answer.objects.filter(academy__id=academy_id,id=answer_id).first()
        if answer is None:
            raise ValidationException('This survey does not exist for this academy')

        serializer = BigAnswerSerializer(answer)
        return Response(serializer.data, status=status.HTTP_200_OK)

class SurveyView(APIView, HeaderLimitOffsetPagination):
    """
    List all snippets, or create a new snippet.
    """
    @capable_of('crud_survey')
    def post(self, request, academy_id=None):

        serializer = SurveySerializer(data=request.data, context={ "request": request, "academy_id": academy_id })
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
            raise ValidationException("Missing survey_id")

        survey = Survey.objects.filter(id=survey_id).first()
        if survey is None:
            raise NotFound('This survey does not exist')

        serializer = SurveyPUTSerializer(survey, data=request.data, context={ "request": request, "survey": survey_id, "academy_id": academy_id })
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

        items = items.filter(**lookup).order_by('-created_at')

        page = self.paginate_queryset(items, request)
        serializer = SurveySerializer(page, many=True)

        if self.is_paginate(request):
            return self.get_paginated_response(serializer.data)
        else:
            return Response(serializer.data, status=status.HTTP_200_OK)