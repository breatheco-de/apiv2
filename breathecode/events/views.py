from breathecode.events.actions import fix_datetime_weekday
import os

from django.contrib.auth.models import User
from django.db.models.query_utils import Q
from breathecode.authenticate.actions import server_id
from breathecode.events.caches import EventCache
from datetime import datetime, timedelta
import logging
import re

from django.http.response import HttpResponse
from breathecode.utils.cache import Cache
from django.shortcuts import render
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from .models import Event, EventType, EventCheckin, Venue
from breathecode.admissions.models import Academy, Cohort, CohortTimeSlot, CohortUser
from rest_framework.decorators import api_view, permission_classes
from .serializers import (EventSerializer, EventSmallSerializer,
                          EventTypeSerializer, EventCheckinSerializer,
                          EventSmallSerializerNoAcademy, VenueSerializer)
from rest_framework.response import Response
from rest_framework.views import APIView
# from django.http import HttpResponse
from rest_framework.response import Response
from breathecode.utils import ValidationException, capable_of, HeaderLimitOffsetPagination
from rest_framework.decorators import renderer_classes
from breathecode.renderers import PlainTextRenderer
from breathecode.services.eventbrite import Eventbrite
from .tasks import async_eventbrite_webhook
from breathecode.utils import ValidationException
from icalendar import Calendar as iCalendar, Event as iEvent, vCalAddress, vText

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
        lookup['academy__slug__in'] = value.split(",")

    lookup['starting_at__gte'] = timezone.now()
    if 'past' in request.GET:
        if request.GET.get('past') == "true":
            lookup.pop("starting_at__gte")
            lookup['starting_at__lte'] = timezone.now()

    items = items.filter(**lookup).order_by('starting_at')

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


class AcademyEventView(APIView, HeaderLimitOffsetPagination):
    """
    List all snippets, or create a new snippet.
    """
    cache = EventCache()

    @capable_of('read_event')
    def get(self, request, format=None, academy_id=None, event_id=None):
        city = self.request.GET.get('city')
        country = self.request.GET.get('country')
        zip_code = self.request.GET.get('zip_code')
        upcoming = self.request.GET.get('upcoming')
        past = self.request.GET.get('past')

        cache_kwargs = {
            'academy_id': academy_id,
            'event_id': event_id,
            'city': city,
            'country': country,
            'zip_code': zip_code,
            'upcoming': upcoming,
            'past': past,
            **self.pagination_params(request),
        }

        cache = self.cache.get(**cache_kwargs)
        if cache:
            return Response(cache, status=status.HTTP_200_OK)

        if event_id is not None:
            single_event = Event.objects.filter(
                id=event_id, academy__id=academy_id).first()
            if single_event is None:
                raise ValidationException("Event not found", 404)

            serializer = EventSmallSerializer(single_event, many=False)
            self.cache.set(serializer.data, **cache_kwargs)
            return Response(serializer.data)

        items = Event.objects.filter(academy__id=academy_id)
        lookup = {}

        if city:
            lookup['venue__city__iexact'] = city

        if country:
            lookup['venue__country__iexact'] = country

        if zip_code:
            lookup['venue__zip_code'] = zip_code

        if upcoming:
            lookup['starting_at__gte'] = timezone.now()
        elif past:
            if 'starting_at__gte' in lookup:
                lookup.pop("starting_at__gte")
            if past == "true":
                lookup['starting_at__lte'] = timezone.now()

        items = items.filter(**lookup).order_by('-starting_at')

        page = self.paginate_queryset(items, request)
        serializer = EventSmallSerializerNoAcademy(page, many=True)

        if self.is_paginate(request):
            return self.get_paginated_response(serializer.data,
                                               cache=self.cache,
                                               cache_kwargs=cache_kwargs)
        else:
            self.cache.set(serializer.data, **cache_kwargs)
            return Response(serializer.data, status=200)

    @capable_of('crud_event')
    def post(self, request, format=None, academy_id=None):
        academy = Academy.objects.filter(id=academy_id).first()
        if academy is None:
            raise ValidationException(f"Academy {academy_id} not found")

        data = {}
        for key in request.data.keys():
            data[key] = request.data.get(key)

        serializer = EventSerializer(data={**data, "academy": academy.id})
        if serializer.is_valid():
            self.cache.clear()
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of('crud_event')
    def put(self, request, academy_id=None, event_id=None):
        already = Event.objects.filter(id=event_id,
                                       academy__id=academy_id).first()
        if already is None:
            raise ValidationException(
                f"Event not found for this academy {academy_id}")

        serializer = EventSerializer(already, data=request.data)
        if serializer.is_valid():
            self.cache.clear()
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


class EventCheckinView(APIView, HeaderLimitOffsetPagination):
    """
    List all snippets, or create a new snippet.
    """
    @capable_of('read_eventcheckin')
    def get(self, request, format=None, academy_id=None):

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
            start_date = datetime.strptime(start, "%Y-%m-%d").date()
            items = items.filter(created_at__gte=start_date)

        end = request.GET.get('end', None)
        if end is not None:
            end_date = datetime.strptime(end, "%Y-%m-%d").date()
            items = items.filter(created_at__lte=end_date)

        items = items.filter(**lookup).order_by('-created_at')

        page = self.paginate_queryset(items, request)
        serializer = EventCheckinSerializer(page, many=True)

        if self.is_paginate(request):
            return self.get_paginated_response(serializer.data)
        else:
            return Response(serializer.data, status=200)


@api_view(['POST'])
@permission_classes([AllowAny])
@renderer_classes([PlainTextRenderer])
def eventbrite_webhook(request, organization_id):
    webhook = Eventbrite.add_webhook_to_log(request.data, organization_id)

    if webhook:
        async_eventbrite_webhook.delay(webhook.id)
    else:
        logger.debug(
            'One request cannot be parsed, maybe you should update `Eventbrite'
            '.add_webhook_to_log`')
        logger.debug(request.data)

    # async_eventbrite_webhook(request.data)
    return Response('ok', content_type='text/plain')


# list venues
class AcademyVenueView(APIView):
    """
    List all snippets
    """
    @capable_of('read_event')
    def get(self, request, format=None, academy_id=None, user_id=None):

        venues = Venue.objects.filter(
            academy__id=academy_id).order_by('-created_at')

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
        items = Cohort.objects.all()

        if not User.objects.filter(id=user_id).count():
            raise ValidationException("Student not exist",
                                      404,
                                      slug='student-not-exist')

        cohort_ids = (CohortUser.objects.filter(user_id=user_id).values_list(
            'cohort_id', flat=True).exclude(cohort__stage='DELETED'))

        items = CohortTimeSlot.objects.filter(
            cohort__id__in=cohort_ids).order_by('id')
        items = items

        upcoming = request.GET.get('upcoming')
        if upcoming == 'true':
            now = timezone.now()
            items = items.filter(cohort__kickoff_date__gte=now)

        key = server_id()

        calendar = iCalendar()
        calendar.add(
            'prodid',
            f'-//BreatheCode//Student Schedule ({user_id}) {key}//EN')
        calendar.add('X-WR-CALNAME', f'Academy - Schedule')
        calendar.add('X-WR-CALDESC', '')
        calendar.add('REFRESH-INTERVAL;VALUE=DURATION', 'PT15M')

        url = os.getenv('API_URL')
        if url:
            url = re.sub(r'/$', '',
                         url) + '/v1/events/ical/student/' + str(user_id)
            calendar.add('url', url)

        calendar.add('version', '2.0')

        for item in items:
            event = iEvent()

            event.add('summary', item.cohort.name)
            event.add('uid', f'breathecode_cohort_time_slot_{item.id}_{key}')

            event.add('dtstart', item.starting_at)
            event.add('dtstamp', item.starting_at)

            until_date = item.cohort.ending_date

            if not until_date:
                until_date = timezone.make_aware(
                    datetime(year=2100,
                             month=12,
                             day=31,
                             hour=12,
                             minute=00,
                             second=00))

            if item.recurrent:
                event.add('rrule', {
                    'freq': item.recurrency_type,
                    'until': until_date
                })

            event.add('dtend', item.ending_at)

            teacher = CohortUser.objects.filter(
                role='TEACHER', cohort__id=item.cohort.id).first()

            if teacher:
                organizer = vCalAddress(f'MAILTO:{teacher.user.email}')

                if teacher.user.first_name and teacher.user.last_name:
                    organizer.params['cn'] = vText(
                        f'{teacher.user.first_name} '
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
            event['location'] = vText(item.cohort.academy.name)

            calendar.add_component(event)

        calendar_text = calendar.to_ical()

        response = HttpResponse(calendar_text, content_type='text/calendar')
        response['Content-Disposition'] = 'attachment; filename="calendar.ics"'
        return response


class ICalCohortsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        items = Cohort.objects.all()

        ids = request.GET.get('academy', '')
        slugs = request.GET.get('academy_slug', '')

        ids = ids.split(",") if ids else []
        slugs = slugs.split(",") if slugs else []

        if ids:
            items = Cohort.objects.filter(academy__id__in=ids).order_by('id')

        elif slugs:
            items = Cohort.objects.filter(
                academy__slug__in=slugs).order_by('id')

        else:
            items = []

        if not ids and not slugs:
            raise ValidationException(
                "You need to specify at least one academy or academy_slug (comma separated) in the querystring"
            )

        if (Academy.objects.filter(id__in=ids).count() != len(ids) or
                Academy.objects.filter(slug__in=slugs).count() != len(slugs)):
            raise ValidationException("Some academy not exist")

        items = items.exclude(stage='DELETED')

        upcoming = request.GET.get('upcoming')
        if upcoming == 'true':
            now = timezone.now()
            items = items.filter(kickoff_date__gte=now)

        academies_repr = ical_academies_repr(ids=ids, slugs=slugs)
        key = server_id()

        calendar = iCalendar()
        calendar.add(
            'prodid',
            f'-//BreatheCode//Academy Cohorts{academies_repr} {key}//EN')
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

            timeslots = CohortTimeSlot.objects.filter(cohort__id=item.id)
            first_timeslot = timeslots.order_by('starting_at').first()

            if first_timeslot:
                event_first_day.add('summary', f'{item.name} - First day')
                event_first_day.add(
                    'uid', f'breathecode_cohort_{item.id}_first_{key}')
                event_first_day.add('dtstart', first_timeslot.starting_at)
                event_first_day.add('dtend', first_timeslot.ending_at)
                event_first_day.add('dtstamp', first_timeslot.created_at)

            if item.ending_date:
                event.add('dtend', item.ending_date)
                timeslots_datetime = []

                for timeslot in timeslots:
                    starting_at = timeslot.starting_at
                    ending_at = timeslot.ending_at
                    diff = ending_at - starting_at

                    if timeslot.recurrent:
                        ending_at = fix_datetime_weekday(item.ending_date,
                                                         ending_at,
                                                         prev=True)
                        starting_at = ending_at - diff

                    timeslots_datetime.append((starting_at, ending_at))

                last_timeslot = None

                if timeslots_datetime:
                    timeslots_datetime.sort(key=lambda x: x[1], reverse=True)
                    last_timeslot = timeslots_datetime[0]
                    has_last_day = True

                    event_last_day.add('summary', f'{item.name} - Last day')
                    event_last_day.add(
                        'uid', f'breathecode_cohort_{item.id}_last_{key}')
                    event_last_day.add('dtstart', last_timeslot[0])
                    event_last_day.add('dtend', last_timeslot[1])
                    event_last_day.add('dtstamp', item.created_at)

            event.add('dtstamp', item.created_at)

            teacher = CohortUser.objects.filter(role='TEACHER',
                                                cohort__id=item.id).first()

            if teacher:
                organizer = vCalAddress(f'MAILTO:{teacher.user.email}')

                if teacher.user.first_name and teacher.user.last_name:
                    organizer.params['cn'] = vText(
                        f'{teacher.user.first_name} '
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

            event['location'] = vText(item.academy.name)

            if first_timeslot:
                event_first_day['location'] = vText(item.academy.name)

            if has_last_day:
                event_last_day['location'] = vText(item.academy.name)

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

        ids = ids.split(",") if ids else []
        slugs = slugs.split(",") if slugs else []

        if ids:
            items = Event.objects.filter(academy__id__in=ids,
                                         status='ACTIVE').order_by('id')

        elif slugs:
            items = Event.objects.filter(academy__slug__in=slugs,
                                         status='ACTIVE').order_by('id')

        else:
            items = []

        if not ids and not slugs:
            raise ValidationException(
                "You need to specify at least one academy or academy_slug (comma separated) in the querystring"
            )

        if (Academy.objects.filter(id__in=ids).count() != len(ids) or
                Academy.objects.filter(slug__in=slugs).count() != len(slugs)):
            raise ValidationException("Some academy not exist")

        upcoming = request.GET.get('upcoming')
        if upcoming == 'true':
            now = timezone.now()
            items = items.filter(starting_at__gte=now)

        academies_repr = ical_academies_repr(ids=ids, slugs=slugs)
        key = server_id()

        calendar = iCalendar()
        calendar.add(
            'prodid',
            f'-//BreatheCode//Academy Events{academies_repr} {key}//EN')
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

            if item.venue and (item.venue.country or item.venue.state or
                               item.venue.city or item.venue.street_address):
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
