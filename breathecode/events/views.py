from django.shortcuts import render
from django.utils import timezone
from rest_framework.permissions import AllowAny
from .models import Event, EventType, EventCheckin
from rest_framework.decorators import api_view, permission_classes
from .serializers import EventSerializer, EventSmallSerializer, EventTypeSerializer, EventCheckinSerializer
from rest_framework.response import Response
from rest_framework.views import APIView
# Create your views here.

@api_view(['GET'])
@permission_classes([AllowAny])
def get_events(request):
    items = Event.objects.all()
    lookup = {}

    if 'city' in request.GET:
        city = request.GET.get('city')
        lookup['venue__city__iexact'] = city

    if 'country' in request.GET:
        value = request.GET.get('country')
        lookup['venue__country__iexact'] = value
        
    if 'type' in request.GET:
        value = request.GET.get('type')
        lookup['event_type__slug'] = value

    if 'zip_code' in request.GET:
        value = request.GET.get('zip_code')
        lookup['venue__zip_code'] = value

    if 'academy' in request.GET:
        value = request.GET.get('academy')
        lookup['academy__slug__in']=value.split(",")

    lookup['starting_at__gte'] = timezone.now()
    if 'past' in request.GET:
        if request.GET.get('past') == "true":
            lookup.pop("starting_at__gte")
            lookup['starting_at__lte'] = timezone.now()
        
    items = items.filter(**lookup).order_by('-starting_at')
    
    serializer = EventSmallSerializer(items, many=True)
    return Response(serializer.data)

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
