import os

from django.contrib.auth.models import User
from django.db.models.query_utils import Q
from breathecode.authenticate.actions import get_user_language, get_user_settings, server_id
from breathecode.events.caches import EventCache
from .permissions.consumers import event_by_url_param, live_class_by_url_param
from breathecode.utils import APIException
from datetime import datetime, timedelta
from breathecode.utils.views import private_view, render_message, set_query_parameter
from django.shortcuts import redirect, render
import logging
import re
import pytz
from django.core.exceptions import FieldError
from django.contrib.auth.hashers import check_password, make_password

from django.http.response import HttpResponse
from breathecode.utils.api_view_extensions.api_view_extensions import APIViewExtensions
from breathecode.utils.cache import Cache
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from breathecode.utils.decorators import has_permission
from breathecode.utils.i18n import translation

from breathecode.utils.multi_status_response import MultiStatusResponse
from .actions import fix_datetime_weekday, update_timeslots_out_of_range, get_my_event_types
from .models import (Event, EventType, EventCheckin, LiveClass, EventTypeVisibilitySetting, Organization,
                     Venue, EventbriteWebhook, Organizer)
from breathecode.admissions.models import Academy, Cohort, CohortTimeSlot, CohortUser, Syllabus
from rest_framework.decorators import api_view, permission_classes
from .serializers import (EventBigSerializer, EventPublicBigSerializer, GetLiveClassSerializer,
                          LiveClassJoinSerializer, LiveClassSerializer, EventSerializer, EventSmallSerializer,
                          EventTypeSerializer, EventTypeBigSerializer, EventCheckinSerializer,
                          EventSmallSerializerNoAcademy, EventTypeVisibilitySettingSerializer,
                          PostEventTypeSerializer, EventTypePutSerializer, VenueSerializer,
                          OrganizationBigSerializer, OrganizationSerializer, EventbriteWebhookSerializer,
                          OrganizerSmallSerializer, EventCheckinSmallSerializer, PUTEventCheckinSerializer,
                          POSTEventCheckinSerializer)
from rest_framework.response import Response
from rest_framework.views import APIView
# from django.http import HttpResponse
from rest_framework.response import Response
from breathecode.utils import ValidationException, capable_of, HeaderLimitOffsetPagination, DatetimeInteger, GenerateLookupsMixin
from rest_framework.decorators import renderer_classes
from breathecode.renderers import PlainTextRenderer
from breathecode.services.eventbrite import Eventbrite
from .tasks import async_eventbrite_webhook
from breathecode.utils import ValidationException
from breathecode.utils import response_207
from icalendar import Calendar as iCalendar, Event as iEvent, vCalAddress, vText
import breathecode.events.receivers

logger = logging.getLogger(__name__)
MONDAY = 0
TUESDAY = 1
WEDNESDAY = 2
THURSDAY = 3
FRIDAY = 4
SATURDAY = 5
SUNDAY = 6


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
        lookup['academy__slug__in'] = value.split(',')

    if 'status' in request.GET:
        value = request.GET.get('status')
        lookup['status__in'] = value.split(',')
    else:
        lookup['status'] = 'ACTIVE'

    lookup['ending_at__gte'] = timezone.now()
    if 'past' in request.GET:
        if request.GET.get('past') == 'true':
            lookup.pop('ending_at__gte')
            lookup['starting_at__lte'] = timezone.now()

    items = items.filter(**lookup).order_by('starting_at')

    serializer = EventSmallSerializer(items, many=True)
    return Response(serializer.data)


@permission_classes([AllowAny])
class EventView(APIView):
    """
    List all snippets, or create a new snippet.
    """

    def get(self, request, event_id=None):

        if event_id is not None:
            event = Event.objects.get(id=event_id)

            if not event:
                raise ValidationException(translation(lang,
                                                      en='Event not found',
                                                      es='Evento no encontrado',
                                                      slug='event-not-found'),
                                          code=404)

            serializer = EventPublicBigSerializer(event, many=False)
            return Response(serializer.data)

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
            if self.request.GET.get('past') == 'true':
                lookup.pop('starting_at__gte')
                lookup['starting_at__lte'] = timezone.now()

        items = items.filter(**lookup).order_by('-created_at')

        serializer = EventSmallSerializer(items, many=True)
        return Response(serializer.data)

    def post(self, request, format=None):
        serializer = EventSerializer(data=request.data, context={'academy_id': None})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EventMeView(APIView):
    """
    List all snippets, or create a new snippet.
    """

    def get(self, request, event_id=None):

        items = get_my_event_types(request.user)
        lang = get_user_language(request)

        if event_id is not None:
            single_event = Event.objects.filter(id=event_id, event_type__in=items).first()

            if not single_event:
                raise ValidationException(translation(lang,
                                                      en='Event not found or you dont have access',
                                                      es='Evento no encontrado o no tienes acceso',
                                                      slug='not-found'),
                                          code=404)

            _r = self.request.GET.get('redirect', 'false')

            #DEPRECATED: due we have a new endpoint that manages the EventTypeSet consumables
            if _r == 'true':
                if single_event is None:
                    return render_message(request, 'Event not found or you dont have access')
                if single_event.live_stream_url is None or single_event.live_stream_url == '':
                    return render_message(request, 'Event live stream URL is not found')
                return redirect(single_event.live_stream_url, permanent=True)

            serializer = EventBigSerializer(single_event, many=False)
            return Response(serializer.data)

        items = Event.objects.filter(event_type__in=items, status='ACTIVE').order_by('starting_at')
        lookup = {}

        online_event = self.request.GET.get('online_event', '')
        if online_event == 'true':
            lookup['online_event'] = True
        elif online_event == 'false':
            lookup['online_event'] = False

        items = items.filter(**lookup)

        serializer = EventBigSerializer(items, many=True)
        return Response(serializer.data)


class MeLiveClassView(APIView):
    extensions = APIViewExtensions(sort='-starting_at', paginate=True)

    def get(self, request):
        handler = self.extensions(request)

        lang = get_user_language(request)

        query = handler.lookup.build(
            lang,
            strings={
                'exact': [
                    'remote_meeting_url',
                ],
            },
            bools={
                'is_null': ['ended_at'],
            },
            datetimes={
                'gte': ['starting_at'],
                'lte': ['ending_at'],
            },
            slugs=[
                'cohort_time_slot__cohort',
                'cohort_time_slot__cohort__academy',
                'cohort_time_slot__cohort__syllabus_version__syllabus',
            ],
            overwrite={
                'cohort': 'cohort_time_slot__cohort',
                'academy': 'cohort_time_slot__cohort__academy',
                'syllabus': 'cohort_time_slot__cohort__syllabus_version__syllabus',
                'start': 'starting_at',
                'end': 'ending_at',
                'upcoming': 'ended_at',
            },
        )

        items = LiveClass.objects.filter(query, cohort_time_slot__cohort__cohortuser__user=request.user)

        items = handler.queryset(items)
        serializer = GetLiveClassSerializer(items, many=True)

        return handler.response(serializer.data)


@private_view()
@has_permission('live_class_join', consumer=live_class_by_url_param, format='html')
def join_live_class(request, token, live_class, lang):
    now = timezone.now()

    if live_class.starting_at > now:
        return render(request, 'countdown.html', {
            'token': token.key,
            'event': LiveClassJoinSerializer(live_class).data,
        })

    return redirect(live_class.cohort_time_slot.cohort.online_meeting_url, permanent=True)


class AcademyLiveClassView(APIView):
    extensions = APIViewExtensions(sort='-starting_at', paginate=True)

    @capable_of('start_or_end_class')
    def get(self, request, academy_id=None):
        from .models import LiveClass

        handler = self.extensions(request)

        lang = get_user_language(request)

        query = handler.lookup.build(
            lang,
            strings={
                'exact': [
                    'remote_meeting_url',
                    'cohort_time_slot__cohort__cohortuser__user__email',
                ],
            },
            bools={
                'is_null': ['ended_at'],
            },
            datetimes={
                'gte': ['starting_at'],
                'lte': ['ending_at'],
            },
            slugs=[
                'cohort_time_slot__cohort__cohortuser__user',
                'cohort_time_slot__cohort',
                'cohort_time_slot__cohort__academy',
                'cohort_time_slot__cohort__syllabus_version__syllabus',
            ],
            overwrite={
                'cohort': 'cohort_time_slot__cohort',
                'academy': 'cohort_time_slot__cohort__academy',
                'syllabus': 'cohort_time_slot__cohort__syllabus_version__syllabus',
                'start': 'starting_at',
                'end': 'ending_at',
                'upcoming': 'ended_at',
                'user': 'cohort_time_slot__cohort__cohortuser__user',
                'user_email': 'cohort_time_slot__cohort__cohortuser__user__email',
            },
        )

        items = LiveClass.objects.filter(query, cohort_time_slot__cohort__academy__id=academy_id)

        items = handler.queryset(items)
        serializer = GetLiveClassSerializer(items, many=True)

        return handler.response(serializer.data)

    @capable_of('start_or_end_class')
    def post(self, request, academy_id=None):
        lang = get_user_language(request)

        serializer = LiveClassSerializer(data=request.data,
                                         context={
                                             'lang': lang,
                                             'academy_id': academy_id,
                                         })
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of('start_or_end_class')
    def put(self, request, cohort_schedule_id, academy_id=None):
        lang = get_user_language(request)

        already = LiveClass.objects.filter(id=cohort_schedule_id,
                                           cohort_time_slot__cohort__academy__id=academy_id).first()
        if already is None:
            raise ValidationException(
                translation(lang,
                            en=f'Live class not found for this academy {academy_id}',
                            es=f'Clase en vivo no encontrada para esta academia {academy_id}',
                            slug='not-found'))

        serializer = LiveClassSerializer(already,
                                         data=request.data,
                                         context={
                                             'lang': lang,
                                             'academy_id': academy_id,
                                         })
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AcademyLiveClassJoinView(APIView):

    @capable_of('start_or_end_class')
    def get(self, request, hash, academy_id=None):
        lang = get_user_language(request)

        live_class = LiveClass.objects.filter(cohort_time_slot__cohort__cohortuser__user=request.user,
                                              cohort_time_slot__cohort__academy__id=int(academy_id),
                                              hash=hash).first()

        if not live_class:
            raise ValidationException(
                translation(lang,
                            en='Live class not found',
                            es='Clase en vivo no encontrada',
                            slug='not-found'))

        if not live_class.cohort_time_slot.cohort.online_meeting_url:
            message = translation(lang,
                                  en='Live class has no online meeting url',
                                  es='La clase en vivo no tiene una URL de reunión en línea',
                                  slug='no-meeting-url')
            return render_message(request, message, status=400)

        return redirect(live_class.cohort_time_slot.cohort.online_meeting_url, permanent=True)


class AcademyEventView(APIView, GenerateLookupsMixin):
    """
    List all snippets, or create a new snippet.
    """
    extensions = APIViewExtensions(cache=EventCache, sort='-starting_at', paginate=True)

    @capable_of('read_event')
    def get(self, request, academy_id=None, event_id=None):
        handler = self.extensions(request)

        cache = handler.cache.get()
        if cache is not None:
            return Response(cache, status=status.HTTP_200_OK)

        if event_id is not None:
            single_event = Event.objects.filter(id=event_id, academy__id=academy_id).first()
            if single_event is None:
                raise ValidationException('Event not found', 404)

            serializer = EventSmallSerializer(single_event, many=False)
            return handler.response(serializer.data)

        items = Event.objects.filter(academy__id=academy_id)
        lookup = {}

        city = self.request.GET.get('city')
        if city:
            lookup['venue__city__iexact'] = city

        country = self.request.GET.get('country')
        if country:
            lookup['venue__country__iexact'] = country

        zip_code = self.request.GET.get('zip_code')
        if zip_code:
            lookup['venue__zip_code'] = zip_code

        upcoming = self.request.GET.get('upcoming')
        past = self.request.GET.get('past')

        if upcoming:
            lookup['starting_at__gte'] = timezone.now()
        elif past:
            if 'starting_at__gte' in lookup:
                lookup.pop('starting_at__gte')
            if past == 'true':
                lookup['starting_at__lte'] = timezone.now()

        items = items.filter(**lookup)
        items = handler.queryset(items)
        serializer = EventSmallSerializerNoAcademy(items, many=True)

        return handler.response(serializer.data)

    @capable_of('crud_event')
    def post(self, request, format=None, academy_id=None):
        lang = get_user_language(request)

        academy = Academy.objects.filter(id=academy_id).first()
        if academy is None:
            raise ValidationException(
                translation(lang,
                            en=f'Academy {academy_id} not found',
                            es=f'Academia {academy_id} no encontrada',
                            slug='academy-not-found'))

        organization_id = Organization.objects.filter(
            Q(academy__id=academy_id) | Q(organizer__academy__id=academy_id)).values_list('id',
                                                                                          flat=True).first()
        if not organization_id:
            raise ValidationException(
                translation(lang,
                            en=f"Academy {academy.name} doesn\'t have the integrations with Eventbrite done",
                            es=f'La academia {academy.name} no tiene las integraciones con Eventbrite aún',
                            slug='organization-not-exist'))

        data = {}
        for key in request.data.keys():
            data[key] = request.data.get(key)

        data['sync_status'] = 'PENDING'
        data['organization'] = organization_id

        serializer = EventSerializer(data={
            **data, 'academy': academy.id
        },
                                     context={
                                         'lang': lang,
                                         'academy_id': academy_id
                                     })
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of('crud_event')
    def put(self, request, academy_id=None, event_id=None):
        lang = get_user_language(request)

        already = Event.objects.filter(id=event_id, academy__id=academy_id).first()
        if already is None:
            raise ValidationException(
                translation(lang,
                            en=f'Event not found for this academy {academy_id}',
                            es=f'Evento no encontrado para esta academia {academy_id}',
                            slug='event-not-found'))

        organization_id = Organization.objects.filter(
            Q(academy__id=academy_id) | Q(organizer__academy__id=academy_id)).values_list('id',
                                                                                          flat=True).first()
        if not organization_id:
            raise ValidationException(
                translation(
                    lang,
                    en=f"Academy {already.academy.name} doesn\'t have the integrations with Eventbrite done",
                    es=f'La academia {already.academy.name} no tiene las integraciones con Eventbrite aún',
                    slug='organization-not-exist'))

        data = {}
        for key in request.data.keys():
            data[key] = request.data.get(key)

        data['sync_status'] = 'PENDING'
        data['organization'] = organization_id

        serializer = EventSerializer(already, data=data, context={'lang': lang, 'academy_id': academy_id})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of('crud_event')
    def delete(self, request, academy_id=None, event_id=None):
        lookups = self.generate_lookups(request, many_fields=['id'])

        if not lookups and not event_id:
            raise ValidationException('provide arguments in the url',
                                      code=400,
                                      slug='without-lookups-and-event-id')

        if lookups and event_id:
            raise ValidationException(
                'event_id in url '
                'in bulk mode request, use querystring style instead',
                code=400,
                slug='lookups-and-event-id-together')

        if lookups:
            alls = Event.objects.filter(**lookups)
            valids = alls.filter(academy__id=academy_id, status='DRAFT')
            from_other_academy = alls.exclude(academy__id=academy_id)
            not_draft = alls.exclude(status='DRAFT')

            responses = []
            if valids:
                responses.append(MultiStatusResponse(code=204, queryset=valids))

            if from_other_academy:
                responses.append(
                    MultiStatusResponse('Event doest not exist or does not belong to this academy',
                                        code=400,
                                        slug='not-found',
                                        queryset=from_other_academy))

            if not_draft:
                responses.append(
                    MultiStatusResponse('Only draft events can be deleted',
                                        code=400,
                                        slug='non-draft-event',
                                        queryset=not_draft))

            if from_other_academy or not_draft:
                response = response_207(responses, 'slug')
                valids.delete()
                return response

            valids.delete()
            return Response(None, status=status.HTTP_204_NO_CONTENT)

        event = Event.objects.filter(academy__id=academy_id, id=event_id).first()
        if event is None:
            raise ValidationException('Event doest not exist or does not belong to this academy',
                                      slug='not-found')

        if event.status != 'DRAFT':
            raise ValidationException('Only draft events can be deleted', slug='non-draft-event')

        event.delete()
        return Response(None, status=status.HTTP_204_NO_CONTENT)


class AcademyEventJoinView(APIView):

    @capable_of('start_or_end_event')
    def get(self, request, event_id, academy_id=None):
        lang = get_user_language(request)

        event = Event.objects.filter(academy__id=int(academy_id), id=event_id).first()

        if not event:
            raise ValidationException(
                translation(lang, en='Event not found', es='Evento no encontrado', slug='not-found'))

        if not event.live_stream_url:
            message = translation(lang,
                                  en='Event has no live stream url',
                                  es='Evento no tiene url de live stream',
                                  slug='no-live-stream-url')
            return render_message(request, message, status=400)

        return redirect(event.live_stream_url, permanent=True)


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

        if 'allow_shared_creation' in self.request.GET:
            value = self.request.GET.get('allow_shared_creation', '').lower()
            lookup['allow_shared_creation'] = value == 'true'

        items = items.filter(**lookup).order_by('-created_at')

        serializer = EventTypeSerializer(items, many=True)
        return Response(serializer.data)


class AcademyEventTypeView(APIView):
    """
    List all snippets, or create a new snippet.
    """

    @capable_of('read_event_type')
    def get(self, request, academy_id=None, event_type_slug=None):

        if event_type_slug is not None:
            event_type = EventType.objects.filter(academy__id=academy_id, slug=event_type_slug).first()
            if not event_type:
                raise ValidationException('Event Type not found for this academy',
                                          slug='event-type-not-found')

            serializer = EventTypeBigSerializer(event_type, many=False)
            return Response(serializer.data)

        items = EventType.objects.filter(Q(academy__id=academy_id) | Q(allow_shared_creation=True))
        lookup = {}

        if 'academy' in self.request.GET:
            value = self.request.GET.get('academy')
            lookup['academy__slug'] = value

        if 'allow_shared_creation' in self.request.GET:
            value = self.request.GET.get('allow_shared_creation', '').lower()
            lookup['allow_shared_creation'] = value == 'true'

        items = items.filter(**lookup).order_by('-created_at')

        serializer = EventTypeSerializer(items, many=True)
        return Response(serializer.data)

    @capable_of('crud_event_type')
    def post(self, request, academy_id):
        serializer = PostEventTypeSerializer(data=request.data, context={'academy_id': academy_id})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of('crud_event_type')
    def put(self, request, academy_id, event_type_slug=None):
        event_type = EventType.objects.filter(academy__id=academy_id, slug=event_type_slug).first()
        if not event_type:
            raise ValidationException('Event Type not found for this academy', slug='event-type-not-found')
        serializer = EventTypePutSerializer(event_type, data=request.data, context={'academy_id': academy_id})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EventTypeVisibilitySettingView(APIView):
    """
    Show the visibility settings of a EventType.
    """

    extensions = APIViewExtensions(sort='-id')

    @capable_of('read_event_type')
    def get(self, request, event_type_slug, academy_id=None):
        handler = self.extensions(request)
        lang = get_user_language(request)

        event_type = EventType.objects.filter(slug=event_type_slug).first()
        if not event_type:
            raise ValidationException(
                translation(lang,
                            en='Event type not found',
                            es='Tipo de evento no encontrado',
                            slug='not-found'), )

        if event_type.allow_shared_creation or event_type.academy.id == academy_id:
            items = event_type.visibility_settings.filter(academy__id=academy_id)

        # avoid show the visibility settings from a other academy if allow_shared_creation is false
        else:
            items = EventTypeVisibilitySetting.objects.none()

        items = handler.queryset(items)
        serializer = EventTypeVisibilitySettingSerializer(items, many=True)
        return handler.response(serializer.data)

    @capable_of('crud_event_type')
    def post(self, request, event_type_slug, academy_id=None):
        handler = self.extensions(request)
        lang = get_user_language(request)

        academy = Academy.objects.filter(id=academy_id).first()

        event_type = EventType.objects.filter(slug=event_type_slug, academy=academy_id).first()
        if not event_type:
            raise ValidationException(
                translation(lang,
                            en='Event type not found',
                            es='Tipo de evento no encontrado',
                            slug='event-type-not-found'), )

        syllabus = None
        if 'syllabus' in request.data:
            syllabus = Syllabus.objects.filter(Q(academy_owner__id=academy_id) | Q(private=False),
                                               id=request.data['syllabus']).first()
            if syllabus is None:
                raise ValidationException(
                    translation(lang,
                                en='Syllabus not found',
                                es='Syllabus no encontrado',
                                slug='syllabus-not-found'), )

        cohort = None
        if 'cohort' in request.data:
            cohort = Cohort.objects.filter(id=request.data['cohort'], academy=academy_id).first()
            if cohort is None:
                raise ValidationException(
                    translation(lang,
                                en='Cohort not found',
                                es='Cohorte no encontrada',
                                slug='cohort-not-found'), )

        visibility_setting, created = EventTypeVisibilitySetting.objects.get_or_create(syllabus=syllabus,
                                                                                       academy=academy,
                                                                                       cohort=cohort)

        if not event_type.visibility_settings.filter(id=visibility_setting.id).exists():
            event_type.visibility_settings.add(visibility_setting)

        serializer = EventTypeVisibilitySettingSerializer(visibility_setting, many=False)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @capable_of('crud_event_type')
    def delete(self, request, event_type_slug, visibility_setting_id=None, academy_id=None):
        lang = get_user_language(request)

        event_type = EventType.objects.filter(slug=event_type_slug, academy=academy_id).first()
        if not event_type:
            raise ValidationException(
                translation(lang,
                            en='Event type not found',
                            es='Tipo de evento no encontrado',
                            slug='event-type-not-found'), )

        item = EventTypeVisibilitySetting.objects.filter(id=visibility_setting_id, academy=academy_id).first()

        if not item:
            raise ValidationException(translation(lang,
                                                  en='Event type visibility setting not found',
                                                  es='Configuración de visibilidad no encontrada',
                                                  slug='event-type-visibility-setting-not-found'),
                                      code=404)

        other_event_type = EventType.objects.filter(
            visibility_settings__id=visibility_setting_id,
            academy=academy_id).exclude(slug=event_type_slug).exists()

        if other_event_type:
            event_type.visibility_settings.remove(item)
            return Response(None, status=status.HTTP_204_NO_CONTENT)

        item.delete()

        return Response(None, status=status.HTTP_204_NO_CONTENT)


@private_view()
@has_permission('event_join', consumer=event_by_url_param, format='html')
def join_event(request, token, event):
    now = timezone.now()

    if event.starting_at > now:
        return render(request, 'countdown.html', {
            'token': token.key,
            'event': EventSmallSerializer(event).data,
        })

    # if the event is happening right now and I have not joined yet
    checkin = EventCheckin.objects.filter(Q(email=token.user.email) | Q(attendee=token.user),
                                          event=event).first()
    if checkin is None:
        checkin = EventCheckin(event=event, attendee=token.user, email=token.user.email)

    if checkin.attended_at is None:

        checkin.status = 'DONE'
        checkin.attended_at = now
        checkin.save()

    return redirect(event.live_stream_url, permanent=True)


class EventCheckinView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, event_id):
        if event_id is None:
            raise ValidationException(f'event_id must not be null', status.HTTP_404_NOT_FOUND)

        try:
            event_id = int(event_id)
        except:
            raise ValidationException(f'{event_id} must be am integer', slug='Event must be an integer')

        event_checkins = EventCheckin.objects.filter(event=event_id)

        serializer = EventCheckinSmallSerializer(event_checkins, many=True)

        return Response(serializer.data)


class EventMeCheckinView(APIView):
    """
    List all snippets, or create a new snippet.
    """

    def put(self, request, event_id):
        lang = get_user_language(request)
        items = get_my_event_types(request.user)

        event = Event.objects.filter(event_type__in=items, id=event_id).first()
        if event is None:
            raise ValidationException(translation(lang,
                                                  en='Event not found or you dont have access',
                                                  es='Evento no encontrado o no tienes acceso',
                                                  slug='event-not-found'),
                                      code=404)

        serializer = PUTEventCheckinSerializer(event, request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, event_id):
        lang = get_user_language(request)
        items = get_my_event_types(request.user)

        event = Event.objects.filter(event_type__in=items, id=event_id).first()
        if event is None:
            raise ValidationException(translation(lang,
                                                  en='Event not found or you dont have access',
                                                  es='Evento no encontrado o no tienes acceso',
                                                  slug='event-not-found'),
                                      code=404)

        serializer = POSTEventCheckinSerializer(data={
            **request.data, 'email': request.user.email,
            'attendee': request.user.id,
            'event': event.id
        },
                                                context={
                                                    'lang': lang,
                                                    'user': request.user
                                                })
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AcademyEventCheckinView(APIView):
    """
    List all snippets, or create a new snippet.
    """

    extensions = APIViewExtensions(sort='-created_at', paginate=True)

    @capable_of('read_eventcheckin')
    def get(self, request, format=None, academy_id=None):
        handler = self.extensions(request)

        items = EventCheckin.objects.filter(event__academy__id=academy_id)
        lookup = {}

        if 'status' in self.request.GET:
            value = self.request.GET.get('status')
            lookup['status'] = value

        if 'event' in self.request.GET:
            value = self.request.GET.get('event')
            lookup['event__id'] = value

        like = self.request.GET.get('like')
        if 'like' in self.request.GET:
            items = items.filter(
                Q(attendee__first_name__icontains=like)
                | Q(attendee__last_name_icontains=like)
                | Q(attendee__email_icontains=like) | Q(email_icontains=like))

        start = request.GET.get('start', None)
        if start is not None:
            start_date = datetime.strptime(start, '%Y-%m-%d').date()
            items = items.filter(created_at__gte=start_date)

        end = request.GET.get('end', None)
        if end is not None:
            end_date = datetime.strptime(end, '%Y-%m-%d').date()
            items = items.filter(created_at__lte=end_date)

        items = items.filter(**lookup)
        items = handler.queryset(items)
        serializer = EventCheckinSerializer(items, many=True)

        return handler.response(serializer.data)


@api_view(['POST'])
@permission_classes([AllowAny])
@renderer_classes([PlainTextRenderer])
def eventbrite_webhook(request, organization_id):
    webhook = Eventbrite.add_webhook_to_log(request.data, organization_id)

    if webhook:
        async_eventbrite_webhook.delay(webhook.id)
    else:
        logger.debug('One request cannot be parsed, maybe you should update `Eventbrite'
                     '.add_webhook_to_log`')
        logger.debug(request.data)

    # async_eventbrite_webhook(request.data)
    return Response('ok', content_type='text/plain')


class AcademyOrganizerView(APIView):
    """
    List all snippets
    """

    @capable_of('read_organization')
    def get(self, request, academy_id=None):

        orgs = Organizer.objects.filter(academy__id=academy_id)
        if orgs is None:
            raise ValidationException('Organizers not found for this academy', 404)

        serializer = OrganizerSmallSerializer(orgs, many=True)
        return Response(serializer.data)


# list venues
class AcademyOrganizationOrganizerView(APIView):
    """
    List all snippets
    """

    @capable_of('read_organization')
    def get(self, request, academy_id=None):

        org = Organization.objects.filter(academy__id=academy_id).first()
        if org is None:
            raise ValidationException('Organization not found for this academy', 404)

        organizers = Organizer.objects.filter(organization_id=org.id)
        serializer = OrganizerSmallSerializer(organizers, many=True)
        return Response(serializer.data)

    @capable_of('crud_organization')
    def delete(self, request, academy_id=None, organizer_id=None):

        org = Organization.objects.filter(academy__id=academy_id).first()
        if org is None:
            raise ValidationException('Organization not found for this academy', 404)

        organizer = Organizer.objects.filter(organization_id=org.id, id=organizer_id).first()
        if organizer is None:
            raise ValidationException('Organizers not found for this academy organization', 404)

        organizer.academy = None
        organizer.save()

        serializer = OrganizerSmallSerializer(organizer, many=False)
        return Response(serializer.data)


# list venues
class AcademyOrganizationView(APIView):
    """
    List all snippets
    """

    @capable_of('read_organization')
    def get(self, request, academy_id=None):

        org = Organization.objects.filter(academy__id=academy_id).first()
        if org is None:
            raise ValidationException('Organization not found for this academy', 404)

        serializer = OrganizationBigSerializer(org, many=False)
        return Response(serializer.data)

    @capable_of('crud_organization')
    def post(self, request, format=None, academy_id=None):

        organization = Organization.objects.filter(academy__id=academy_id).first()
        if organization:
            raise ValidationException('Academy already has an organization asociated', slug='already-created')

        serializer = OrganizationSerializer(data={**request.data, 'academy': academy_id})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of('crud_organization')
    def put(self, request, format=None, academy_id=None):

        organization = Organization.objects.filter(academy__id=academy_id).first()
        if not organization:
            raise ValidationException('Organization not found for this academy', slug='org-not-found')

        serializer = OrganizationSerializer(organization, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of('crud_organization')
    def delete(self, request, format=None, academy_id=None):

        organization = Organization.objects.filter(academy__id=academy_id).first()
        if not organization:
            raise ValidationException('Organization not found for this academy', slug='org-not-found')

        organization.delete()

        return Response(None, status=status.HTTP_204_NO_CONTENT)


# list eventbride webhook
class OrganizationWebhookView(APIView, HeaderLimitOffsetPagination):

    @capable_of('read_organization')
    def get(self, request, academy_id=None):

        org = Organization.objects.filter(academy__id=academy_id).first()
        if not org:
            raise ValidationException(f'Academy has no organization', code=400, slug='organization-no-found')

        webhooks = EventbriteWebhook.objects.filter(organization_id=org.id).order_by('-updated_at')
        page = self.paginate_queryset(webhooks, request)
        serializer = EventbriteWebhookSerializer(page, many=True)
        if self.is_paginate(request):
            return self.get_paginated_response(serializer.data)
        else:
            return Response(serializer.data, status=200)


# list venues
class AcademyVenueView(APIView):
    """
    List all snippets
    """

    @capable_of('read_event')
    def get(self, request, format=None, academy_id=None, user_id=None):

        venues = Venue.objects.filter(academy__id=academy_id).order_by('-created_at')

        serializer = VenueSerializer(venues, many=True)
        return Response(serializer.data)


def ical_academies_repr(slugs=None, ids=None):
    ret = []

    if not ids:
        ids = []

    if not slugs:
        slugs = []

    if ids:
        ret = ret + \
            list(Academy.objects.filter(id__in=ids).values_list('id', flat=True))

    if slugs:
        ret = ret + \
            list(Academy.objects.filter(
                slug__in=slugs).values_list('id', flat=True))

    ret = sorted(list(dict.fromkeys(ret)))
    ret = ','.join([str(id) for id in ret])

    if ret:
        ret = f' ({ret})'

    return ret


class ICalStudentView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, user_id):
        if not User.objects.filter(id=user_id).count():
            raise ValidationException('Student not exist', 404, slug='student-not-exist')

        cohort_ids = (CohortUser.objects.filter(user__id=user_id,
                                                cohort__ending_date__isnull=False,
                                                cohort__never_ends=False).values_list(
                                                    'cohort_id', flat=True).exclude(cohort__stage='DELETED'))

        items = CohortTimeSlot.objects.filter(cohort__id__in=cohort_ids).order_by('id')

        upcoming = request.GET.get('upcoming')
        if upcoming == 'true':
            now = timezone.now()
            items = items.filter(cohort__kickoff_date__gte=now)

        key = server_id()

        calendar = iCalendar()
        calendar.add('prodid', f'-//BreatheCode//Student Schedule ({user_id}) {key}//EN')
        calendar.add('METHOD', 'PUBLISH')
        calendar.add('X-WR-CALNAME', f'Academy - Schedule')
        calendar.add('X-WR-CALDESC', '')
        calendar.add('REFRESH-INTERVAL;VALUE=DURATION', 'PT15M')

        url = os.getenv('API_URL')
        if url:
            url = re.sub(r'/$', '', url) + '/v1/events/ical/student/' + str(user_id)
            calendar.add('url', url)

        calendar.add('version', '2.0')

        for item in items:
            event = iEvent()

            event.add('summary', item.cohort.name)
            event.add('uid', f'breathecode_cohort_time_slot_{item.id}_{key}')

            stamp = DatetimeInteger.to_datetime(item.timezone, item.starting_at)
            starting_at = fix_datetime_weekday(item.cohort.kickoff_date, stamp, next=True)
            event.add('dtstart', starting_at)
            event.add('dtstamp', stamp)

            until_date = item.removed_at or item.cohort.ending_date

            if not until_date:
                until_date = timezone.make_aware(
                    datetime(year=2100, month=12, day=31, hour=12, minute=00, second=00))

            ending_at = DatetimeInteger.to_datetime(item.timezone, item.ending_at)
            ending_at = fix_datetime_weekday(item.cohort.kickoff_date, ending_at, next=True)
            event.add('dtend', ending_at)

            if item.recurrent:
                utc_ending_at = ending_at.astimezone(pytz.UTC)

                # is possible hour of cohort.ending_date are wrong filled, I's assumes the max diff between
                # summer/winter timezone should have two hours
                delta = timedelta(hours=utc_ending_at.hour - until_date.hour + 3,
                                  minutes=utc_ending_at.minute - until_date.minute,
                                  seconds=utc_ending_at.second - until_date.second)

                event.add('rrule', {'freq': item.recurrency_type, 'until': until_date + delta})

            teacher = CohortUser.objects.filter(role='TEACHER', cohort__id=item.cohort.id).first()

            if teacher:
                organizer = vCalAddress(f'MAILTO:{teacher.user.email}')

                if teacher.user.first_name and teacher.user.last_name:
                    organizer.params['cn'] = vText(f'{teacher.user.first_name} '
                                                   f'{teacher.user.last_name}')
                elif teacher.user.first_name:
                    organizer.params['cn'] = vText(teacher.user.first_name)
                elif teacher.user.last_name:
                    organizer.params['cn'] = vText(teacher.user.last_name)

                organizer.params['role'] = vText('OWNER')
                event['organizer'] = organizer

            location = item.cohort.academy.name

            if item.cohort.academy.website_url:
                location = f'{location} ({item.cohort.academy.website_url})'
            event['location'] = vText(item.cohort.online_meeting_url or item.cohort.academy.name)

            calendar.add_component(event)

        calendar_text = calendar.to_ical()

        response = HttpResponse(calendar_text, content_type='text/calendar')
        response['Content-Disposition'] = 'attachment; filename="calendar.ics"'
        return response


class ICalCohortsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        ids = request.GET.get('academy', '')
        slugs = request.GET.get('academy_slug', '')

        ids = ids.split(',') if ids else []
        slugs = slugs.split(',') if slugs else []

        if ids:
            items = Cohort.objects.filter(ending_date__isnull=False, never_ends=False,
                                          academy__id__in=ids).order_by('id')

        elif slugs:
            items = Cohort.objects.filter(ending_date__isnull=False,
                                          never_ends=False,
                                          academy__slug__in=slugs).order_by('id')

        else:
            items = []

        if not ids and not slugs:
            raise ValidationException(
                'You need to specify at least one academy or academy_slug (comma separated) in the querystring'
            )

        if (Academy.objects.filter(id__in=ids).count() != len(ids)
                or Academy.objects.filter(slug__in=slugs).count() != len(slugs)):
            raise ValidationException('Some academy not exist')

        items = items.exclude(stage='DELETED')

        upcoming = request.GET.get('upcoming')
        if upcoming == 'true':
            now = timezone.now()
            items = items.filter(kickoff_date__gte=now)

        academies_repr = ical_academies_repr(ids=ids, slugs=slugs)
        key = server_id()

        calendar = iCalendar()
        calendar.add('prodid', f'-//BreatheCode//Academy Cohorts{academies_repr} {key}//EN')
        calendar.add('METHOD', 'PUBLISH')
        calendar.add('X-WR-CALNAME', f'Academy - Cohorts')
        calendar.add('X-WR-CALDESC', '')
        calendar.add('REFRESH-INTERVAL;VALUE=DURATION', 'PT15M')

        url = os.getenv('API_URL')
        if url:
            url = re.sub(r'/$', '', url) + '/v1/events/ical/cohorts'
            if ids or slugs:
                url = url + '?'

                if ids:
                    url = url + 'academy=' + ','.join(ids)

                if ids and slugs:
                    url = url + '&'

                if slugs:
                    url = url + 'academy_slug=' + ','.join(slugs)

            calendar.add('url', url)

        calendar.add('version', '2.0')

        for item in items:
            event = iEvent()
            event_first_day = iEvent()
            event_last_day = iEvent()
            has_last_day = False

            event.add('summary', item.name)
            event.add('uid', f'breathecode_cohort_{item.id}_{key}')
            event.add('dtstart', item.kickoff_date)

            timeslots = update_timeslots_out_of_range(item.kickoff_date, item.ending_date,
                                                      CohortTimeSlot.objects.filter(cohort__id=item.id))

            first_timeslot = timeslots[0] if timeslots else None
            if first_timeslot:
                recurrent = first_timeslot['recurrent']
                starting_at = first_timeslot['starting_at'] if not recurrent else fix_datetime_weekday(
                    item.kickoff_date, first_timeslot['starting_at'], next=True)
                ending_at = first_timeslot['ending_at'] if not recurrent else fix_datetime_weekday(
                    item.kickoff_date, first_timeslot['ending_at'], next=True)

                event_first_day.add('summary', f'{item.name} - First day')
                event_first_day.add('uid', f'breathecode_cohort_{item.id}_first_{key}')
                event_first_day.add('dtstart', starting_at)
                event_first_day.add('dtend', ending_at)
                event_first_day.add('dtstamp', first_timeslot['created_at'])

            if item.ending_date:
                event.add('dtend', item.ending_date)
                timeslots_datetime = []

                # fix the datetime to be use for get the last day
                for timeslot in timeslots:
                    starting_at = timeslot['starting_at']
                    ending_at = timeslot['ending_at']
                    diff = ending_at - starting_at

                    if timeslot['recurrent']:
                        ending_at = fix_datetime_weekday(item.ending_date, ending_at, prev=True)
                        starting_at = ending_at - diff

                    timeslots_datetime.append((starting_at, ending_at))

                last_timeslot = None

                if timeslots_datetime:
                    timeslots_datetime.sort(key=lambda x: x[1], reverse=True)
                    last_timeslot = timeslots_datetime[0]
                    has_last_day = True

                    event_last_day.add('summary', f'{item.name} - Last day')

                    event_last_day.add('uid', f'breathecode_cohort_{item.id}_last_{key}')
                    event_last_day.add('dtstart', last_timeslot[0])
                    event_last_day.add('dtend', last_timeslot[1])
                    event_last_day.add('dtstamp', item.created_at)

            event.add('dtstamp', item.created_at)

            teacher = CohortUser.objects.filter(role='TEACHER', cohort__id=item.id).first()

            if teacher:
                organizer = vCalAddress(f'MAILTO:{teacher.user.email}')

                if teacher.user.first_name and teacher.user.last_name:
                    organizer.params['cn'] = vText(f'{teacher.user.first_name} '
                                                   f'{teacher.user.last_name}')
                elif teacher.user.first_name:
                    organizer.params['cn'] = vText(teacher.user.first_name)
                elif teacher.user.last_name:
                    organizer.params['cn'] = vText(teacher.user.last_name)

                organizer.params['role'] = vText('OWNER')
                event['organizer'] = organizer

                if first_timeslot:
                    event_first_day['organizer'] = organizer

                if has_last_day:
                    event_last_day['organizer'] = organizer

            location = item.academy.name

            if item.academy.website_url:
                location = f'{location} ({item.academy.website_url})'

            event['location'] = vText(item.online_meeting_url or item.academy.name)

            if first_timeslot:
                event_first_day['location'] = vText(item.online_meeting_url or item.academy.name)

            if has_last_day:
                event_last_day['location'] = vText(item.online_meeting_url or item.academy.name)

            if first_timeslot:
                calendar.add_component(event_first_day)
            calendar.add_component(event)

            if has_last_day:
                calendar.add_component(event_last_day)

        calendar_text = calendar.to_ical()

        response = HttpResponse(calendar_text, content_type='text/calendar')
        response['Content-Disposition'] = 'attachment; filename="calendar.ics"'
        return response


class ICalEventView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        items = Event.objects.filter(status='ACTIVE')

        ids = request.GET.get('academy', '')
        slugs = request.GET.get('academy_slug', '')

        ids = ids.split(',') if ids else []
        slugs = slugs.split(',') if slugs else []

        if ids:
            items = Event.objects.filter(academy__id__in=ids, status='ACTIVE').order_by('id')

        elif slugs:
            items = Event.objects.filter(academy__slug__in=slugs, status='ACTIVE').order_by('id')

        else:
            items = []

        if not ids and not slugs:
            raise ValidationException(
                'You need to specify at least one academy or academy_slug (comma separated) in the querystring'
            )

        if (Academy.objects.filter(id__in=ids).count() != len(ids)
                or Academy.objects.filter(slug__in=slugs).count() != len(slugs)):
            raise ValidationException('Some academy not exist')

        upcoming = request.GET.get('upcoming')
        if items and upcoming == 'true':
            now = timezone.now()
            items = items.filter(starting_at__gte=now)

        academies_repr = ical_academies_repr(ids=ids, slugs=slugs)
        key = server_id()

        calendar = iCalendar()
        calendar.add('prodid', f'-//BreatheCode//Academy Events{academies_repr} {key}//EN')
        calendar.add('METHOD', 'PUBLISH')
        calendar.add('X-WR-CALNAME', f'Academy - Events')
        calendar.add('X-WR-CALDESC', '')
        calendar.add('REFRESH-INTERVAL;VALUE=DURATION', 'PT15M')

        url = os.getenv('API_URL')
        if url:
            url = re.sub(r'/$', '', url) + '/v1/events/ical/events'
            if ids or slugs:
                url = url + '?'

                if ids:
                    url = url + 'academy=' + ','.join(ids)

                if ids and slugs:
                    url = url + '&'

                if slugs:
                    url = url + 'academy_slug=' + ','.join(slugs)

            calendar.add('url', url)

        calendar.add('version', '2.0')

        for item in items:
            event = iEvent()

            if item.title:
                event.add('summary', item.title)

            description = ''
            description = f'{description}Url: {item.url}\n'

            if item.academy:
                description = f'{description}Academy: {item.academy.name}\n'

            if item.venue and item.venue.title:
                description = f'{description}Venue: {item.venue.title}\n'

            if item.event_type:
                description = f'{description}Event type: {item.event_type.name}\n'

            if item.online_event:
                description = f'{description}Location: online\n'

            event.add('description', description)
            event.add('uid', f'breathecode_event_{item.id}_{key}')
            event.add('dtstart', item.starting_at)
            event.add('dtend', item.ending_at)
            event.add('dtstamp', item.created_at)

            if item.author and item.author.email:
                organizer = vCalAddress(f'MAILTO:{item.author.email}')

                if item.author.first_name and item.author.last_name:
                    organizer.params['cn'] = vText(f'{item.author.first_name} '
                                                   f'{item.author.last_name}')
                elif item.author.first_name:
                    organizer.params['cn'] = vText(item.author.first_name)
                elif item.author.last_name:
                    organizer.params['cn'] = vText(item.author.last_name)

                organizer.params['role'] = vText('OWNER')
                event['organizer'] = organizer

            if item.venue and (item.venue.country or item.venue.state or item.venue.city
                               or item.venue.street_address):
                value = ''

                if item.venue.street_address:
                    value = f'{value}{item.venue.street_address}, '

                if item.venue.city:
                    value = f'{value}{item.venue.city}, '

                if item.venue.state:
                    value = f'{value}{item.venue.state}, '

                if item.venue.country:
                    value = f'{value}{item.venue.country}'

                value = re.sub(', $', '', value)
                event['location'] = vText(value)

            calendar.add_component(event)

        calendar_text = calendar.to_ical()

        response = HttpResponse(calendar_text, content_type='text/calendar')
        response['Content-Disposition'] = 'attachment; filename="calendar.ics"'
        return response
