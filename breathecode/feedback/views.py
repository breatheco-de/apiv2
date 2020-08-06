from django.shortcuts import render
from django.utils import timezone
from .models import Answer
from .serializers import AnswerPOSTSerializer, AnswerSerializer
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

# Create your views here.
class AnswerView(APIView):
    """
    List all snippets, or create a new snippet.
    """
    def get(self, request, format=None):
        
        items = Answer.objects.all()
        lookup = {}

        if 'city' in self.request.GET:
            city = self.request.GET.get('city')
            lookup['venue__city__iexact'] = city

        items = items.filter(**lookup).order_by('-created_at')
        
        serializer = AnswerSerializer(items, many=True)
        return Response(serializer.data)

    def post(self, request, format=None):
        serializer = AnswerPOSTSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)