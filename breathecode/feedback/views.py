from django.shortcuts import render
from django.utils import timezone
from django.http import HttpResponse
from breathecode.admissions.models import CohortUser
from .models import Answer, Survey
from .actions import build_question
from rest_framework import serializers
from rest_framework.exceptions import ValidationError, NotFound
from rest_framework.permissions import AllowAny, IsAuthenticated
from .serializers import AnswerPUTSerializer, AnswerSerializer
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.views import APIView
from rest_framework import status
from breathecode.utils import capable_of, ValidationException
from PIL import Image

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

    cohort_teacher = CohortUser.objects.filter(cohort=survey.cohort, role="TEACHER").first()
    if cohort_teacher is None:
        raise ValidationException("This cohort must have a teacher assigned to be able to survey it", 400)

    _answers = Answer.objects.filter(survey__id=survey_id, user=request.user)
    if _answers.count() == 0:
        _answers = []

        answer = Answer(cohort=survey.cohort, lang=survey.lang)
        question = build_question(answer)
        answer.title = question["title"]
        answer.user = request.user
        answer.lowest = question["lowest"]
        answer.highest = question["highest"]
        answer.survey = survey
        answer.status = 'OPENED'
        answer.opened_at = timezone.now()
        answer.save()
        _answers.append(answer)

        answer = Answer(mentor=cohort_teacher.user, cohort=survey.cohort, lang=survey.lang)
        question = build_question(answer)
        answer.title = question["title"]
        answer.lowest = question["lowest"]
        answer.highest = question["highest"]
        answer.user = request.user
        answer.status = 'OPENED'
        answer.survey = survey
        answer.opened_at = timezone.now()
        answer.save()
        _answers.append(answer)

        answer = Answer(academy=survey.cohort.academy, lang=survey.lang)
        question = build_question(answer)
        answer.title = question["title"]
        answer.lowest = question["lowest"]
        answer.highest = question["highest"]
        answer.user = request.user
        answer.status = 'OPENED'
        answer.survey = survey
        answer.opened_at = timezone.now()
        answer.save()
        _answers.append(answer)
        
    
    serializer = AnswerSerializer(_answers, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

# Create your views here.
class GetAnswerView(APIView):
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

        items = items.filter(**lookup).order_by('-created_at')
        
        serializer = AnswerSerializer(items, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class AnswerView(APIView):
    """
    List all snippets, or create a new snippet.
    """
    def put(self, request, answer_id=None):
        if answer_id is None:
            raise serializers.ValidationError("Missing answer_id", code=400)
        
        answer = Answer.objects.filter(user=request.user,id=answer_id).first()
        if answer is None:
            raise NotFound('This survay does not exist for this user')
        
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
            raise NotFound('This survay does not exist for this user')
        
        serializer = AnswerPUTSerializer(answer)
        return Response(serializer.data, status=status.HTTP_200_OK)
