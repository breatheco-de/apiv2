from django.shortcuts import render
from django.utils import timezone
from .models import Answer
from rest_framework.permissions import AllowAny, IsAuthenticated
from .serializers import AnswerPOSTSerializer, AnswerSerializer
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

        if 'entity_type' in self.request.GET:
            param = self.request.GET.get('entity_type')
            lookup['entity_type'] = param

        if 'entity_id' in self.request.GET:
            param = self.request.GET.get('entity_id')
            lookup['entity_id'] = param

        if 'entity_slug' in self.request.GET:
            param = self.request.GET.get('entity_slug')
            lookup['entity_slug'] = param

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
    def post(self, request, format=None):
        serializer = AnswerPOSTSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)