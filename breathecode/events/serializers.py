from .models import Event
from rest_framework import serializers
import serpy


class CitySerializer(serpy.Serializer):
    name = serpy.Field()


class UserSerializer(serpy.Serializer):
    id = serpy.Field()
    first_name = serpy.Field()
    last_name = serpy.Field()


class AcademySerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()
    city = CitySerializer(required=False)


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
    title = serpy.Field()
    starting_at = serpy.Field()
    ending_at = serpy.Field()
    event_type = EventTypeSmallSerializer(required=False)


class EventSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    excerpt = serpy.Field()
    title = serpy.Field()
    lang = serpy.Field()
    url = serpy.Field()
    banner = serpy.Field()
    description = serpy.Field()
    capacity = serpy.Field()
    starting_at = serpy.Field()
    ending_at = serpy.Field()
    status = serpy.Field()
    event_type = EventTypeSmallSerializer(required=False)
    online_event = serpy.Field()
    venue = VenueSerializer(required=False)
    academy = AcademySerializer(required=False)


class EventSmallSerializerNoAcademy(serpy.Serializer):
    id = serpy.Field()
    excerpt = serpy.Field()
    title = serpy.Field()
    lang = serpy.Field()
    url = serpy.Field()
    banner = serpy.Field()
    starting_at = serpy.Field()
    ending_at = serpy.Field()
    status = serpy.Field()
    event_type = EventTypeSmallSerializer(required=False)
    online_event = serpy.Field()
    venue = VenueSerializer(required=False)


class EventCheckinSerializer(serpy.Serializer):
    id = serpy.Field()
    email = serpy.Field()
    status = serpy.Field()
    created_at = serpy.Field()
    attended_at = serpy.Field()
    attendee = UserSerializer(required=False)
    event = EventTinySerializer()


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        exclude = ()

    def create(self, validated_data):
        # hard-code the organizer to the academy organizer
        try:
            validated_data['organizer'] = validated_data['academy'].organizer
        except:
            pass

        return super().create(validated_data)

    def update(self, instance, validated_data):

        # hard-code the organizer to the academy organizer
        try:
            validated_data['organizer'] = validated_data['academy'].organizer
        except:
            pass

        return super().update(instance, validated_data)
