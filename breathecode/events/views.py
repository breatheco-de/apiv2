from django.shortcuts import render
from django.utils import timezone
from .models import Event, EventType, EventCheckin
from .serializers import EventSerializer, EventSmallSerializer, EventTypeSerializer, EventCheckinSerializer
from rest_framework.response import Response
from rest_framework.views import APIView
# Create your views here.
class EventView(APIView):
    """
    List all snippets, or create a new snippet.
    """
    def get(self, request, format=None):
        
        items = Event.objects.all()
        lookup = {}

        if 'city' in self.request.GET:
            city = self.request.GET.get('city')
            lookup['venue__city__iexact'] = city

        if 'country' in self.request.GET:
            value = self.request.GET.get('city')
            lookup['venue__country__iexact'] = value

        if 'zip_code' in self.request.GET:
            value = self.request.GET.get('city')
            lookup['venue__zip_code'] = value

        lookup['starting_at__gte'] = timezone.now()
        if 'past' in self.request.GET:
            if self.request.GET.get('past') == "true":
                lookup.pop("starting_at__gte")
                lookup['starting_at__lte'] = timezone.now()
            
        items = items.filter(**lookup).order_by('-created_at')
        
        serializer = EventSmallSerializer(items, many=True)
        return Response(serializer.data)

    def post(self, request, format=None):
        serializer = EventSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class EventTypeView(APIView):
    """
    List all snippets, or create a new snippet.
    """
    def get(self, request, format=None):
        
        items = EventType.objects.all()
        lookup = {}

        if 'academy' in self.request.GET:
            value = self.request.GET.get('academy')
            lookup['academy__slug'] = value
            
        items = items.filter(**lookup).order_by('-created_at')
        
        serializer = EventTypeSerializer(items, many=True)
        return Response(serializer.data)

class EventCheckinView(APIView):
    """
    List all snippets, or create a new snippet.
    """
    def get(self, request, format=None):
        
        items = EventCheckin.objects.all()
        lookup = {}

        if 'academy' in self.request.GET:
            value = self.request.GET.get('academy')
            lookup['academy__slug'] = value
            
        items = items.filter(**lookup).order_by('-created_at')
        
        serializer = EventCheckinSerializer(items, many=True)
        return Response(serializer.data)