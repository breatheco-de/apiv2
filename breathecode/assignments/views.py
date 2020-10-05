from .models import Task
from rest_framework.views import APIView
from .serializers import SmallTaskSerializer, PostTaskSerializer
from rest_framework.response import Response
from rest_framework import status


class TaskView(APIView):
    """
    List all snippets, or create a new snippet.
    """
    def get(self, request, format=None):
        items = Task.objects.all()
        serializer = SmallTaskSerializer(items, many=True)
        return Response(serializer.data)

    def post(self, request, format=None):
        serializer = PostTaskSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
