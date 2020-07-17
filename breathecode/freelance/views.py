from django.shortcuts import render
from rest_framework.response import Response
from .serializers import BillSerializer
from rest_framework import status
from rest_framework.decorators import api_view
from .actions import sync_user_issues
from rest_framework.views import APIView

# Create your views here.
class BillView(APIView):
    """
    List all snippets, or create a new snippet.
    """
    def get(self, request, format=None):
        items = Bill.objects.all()
        serializer = BillSerializer(items, many=True)
        return Response(serializer.data)

    def post(self, request, format=None):
        serializer = BillSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Create your views here.
@api_view(['GET'])
def sync_user_issues(request):
    tags = sync_user_issues()
    return Response(tags, status=status.HTTP_200_OK)