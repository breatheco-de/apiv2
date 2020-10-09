from django.shortcuts import render
from django.utils import timezone
from .models import Answer
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from .serializers import AnswerPUTSerializer, AnswerSerializer
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

# Create your views here.
class GetAnswerView(APIView):
    """
    List all snippets, or create a new snippet.
    """
    permission_classes = [AllowAny]
    def get(self, request, format=None):
        
        items = Answer.objects.all()
        lookup = {}

        if 'user' in self.request.GET:
            param = self.request.GET.get('user')
            lookup['user__id'] = param

        if 'cohort' in self.request.GET:
            param = self.request.GET.get('cohort')
            lookup['cohort__slug'] = param

        if 'academy' in self.request.GET:
            param = self.request.GET.get('academy')
            lookup['academy__id'] = param

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
        return Response(serializer.data)

class AnswerView(APIView):
    """
    List all snippets, or create a new snippet.
    """
    def put(self, request, answer_id=None):
        if answer_id is None:
            raise serializers.ValidationError("Missing answer_id", code=400)
        
        answer = Answer.objects.filter(user=request.user,id=answer_id).first()
        if answer is None:
            raise ValidationError('This survay does not exist for this user')
        
        serializer = AnswerPUTSerializer(answer, data=request.data, context={ "request": request, "answer": answer_id })
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)