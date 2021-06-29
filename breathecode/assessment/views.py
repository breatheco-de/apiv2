from django.shortcuts import render
from django.utils import timezone
from django.http import HttpResponse
from breathecode.utils import ValidationException
from .models import Assessment, UserAssessment
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

    ass = UserAssessment.objects.filter(id=user_assessment_id,
                                        status='SENT').first()
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

    def get(self, request, assessment_slug=None):

        if assessment_slug is not None:
            lang = None
            if 'lang' in self.request.GET:
                lang = self.request.GET.get('lang')

            item = Assessment.objects.filter(slug=assessment_slug).first()
            if item is None:
                raise ValidationException("Assessment not found", 404)

            if lang is not None and item.lang != lang:
                item = item.translations.filter(lang=lang).first()
                if item is None:
                    raise ValidationException(
                        f"Language '{lang}' not found for assesment {assessment_slug}",
                        404)

            serializer = GetAssessmentBigSerializer(item, many=False)
            return Response(serializer.data, status=status.HTTP_200_OK)

        # get original all assessments (assessments that have no parent)
        items = Assessment.objects.all()
        lookup = {}

        if 'academy' in self.request.GET:
            param = self.request.GET.get('academy')
            lookup['academy__id'] = param

        if 'lang' in self.request.GET:
            param = self.request.GET.get('lang')
            lookup['lang'] = param
        else:
            items = items.filter(original=None)

        if 'author' in self.request.GET:
            param = self.request.GET.get('author')
            lookup['author__id'] = param

        items = items.filter(**lookup).order_by('-created_at')

        serializer = GetAssessmentSerializer(items, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
