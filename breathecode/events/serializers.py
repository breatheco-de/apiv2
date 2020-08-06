from .models import Event
from rest_framework import serializers
import serpy

class UserSerializer(serpy.Serializer):
    id = serpy.Field()
    first_name = serpy.Field()
    last_name = serpy.Field()

class AcademySerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()

class EventTypeSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()

class EventTypeSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()
    academy = AcademySerializer(required=False)

class VenueSerializer(serpy.Serializer):
    id = serpy.Field()
    title = serpy.Field()
    street_address = serpy.Field()
    city = serpy.Field()
    zip_code = serpy.Field()
    state = serpy.Field()

class EventTinySerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    title = serpy.Field()
    starting_at = serpy.Field()
    ending_at = serpy.Field()
    event_type = EventTypeSmallSerializer()

class EventSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    exerpt = serpy.Field()
    title = serpy.Field()
    lang = serpy.Field()
    url = serpy.Field()
    banner = serpy.Field()
    starting_at = serpy.Field()
    ending_at = serpy.Field()
    event_type = EventTypeSmallSerializer()
    venue = VenueSerializer()
    academy = AcademySerializer()

class EventCheckinSerializer(serpy.Serializer):
    id = serpy.Field()
    email = serpy.Field()
    attendee = UserSerializer()
    event = EventTinySerializer()

class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        exclude = ()

        