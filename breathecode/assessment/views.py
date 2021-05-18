from django.shortcuts import render
from django.utils import timezone
from django.http import HttpResponse
from breathecode.utils import ValidationException
from .models import Assessment, UserAssessment, GetAssessmentView
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from .serializers import GetAssessmentBigSerializer, GetAssessmentSerializer
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.views import APIView
from rest_framework import status
from PIL import Image

@api_view(['GET'])
@permission_classes([AllowAny])
def track_assesment_open(request, user_assessment_id=None):

    ass = UserAssessment.objects.filter(id=user_assessment_id, status='SENT').first()
    if ass is not None:
        ass.status = 'OPENED'
        ass.opened_at = timezone.now()
        ass.save()
    
    image = Image.new('RGB', (1, 1))
    response = HttpResponse(content_type="image/png")
    image.save(response, "PNG")
    return response

# Create your views here.
class GetAssessmentView(APIView):
    """
    List all snippets, or create a new snippet.
    """
    permission_classes = [AllowAny]
    def get(self, request, assessment_id=None):

        if assessment_id is not None:
            item = Assessment.objects.filter(id=assessment_id).first()
            if item is None:
                raise ValidationException("Assessment not found", 404)

            serializer = GetAssessmentBigSerializer(item, many=False)
            return serializer.data

        
        items = Assessment.objects.all()
        lookup = {}

        if 'academy' in self.request.GET:
            param = self.request.GET.get('academy')
            lookup['academy__id'] = param

        if 'lang' in self.request.GET:
            param = self.request.GET.get('lang')
            lookup['lang'] = param

        if 'author' in self.request.GET:
            param = self.request.GET.get('author')
            lookup['author__id'] = param

        items = items.filter(**lookup).order_by('-created_at')
        
        serializer = GetAssessmentSerializer(items, many=True)
        return Response(serializer.data)
