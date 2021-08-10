from breathecode.certificate.models import Specialty
from breathecode.admissions.actions import sync_cohort_timeslots
from breathecode.admissions.caches import CohortCache
import logging
import re
import pytz
from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
from django.shortcuts import render
from django.contrib.auth.models import AnonymousUser
from breathecode.utils import HeaderLimitOffsetPagination
from rest_framework.views import APIView
from django.db.models import Q
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth.models import User
from .serializers import (AcademySerializer, GetSyllabusSerializer, SpecialtyModeTimeSlotSerializer,
                          CohortSerializer, CohortTimeSlotSerializer, GETSpecialtyModeTimeSlotSerializer,
                          GETCohortTimeSlotSerializer, GetCohortSerializer, GetSyllabusVersionSerializer,
                          SyllabusSerializer, SyllabusVersionPutSerializer, SyllabusVersionSerializer,
                          CohortUserSerializer, GETCohortUserSerializer, CohortUserPUTSerializer,
                          CohortPUTSerializer, UserDJangoRestSerializer, UserMeSerializer,
                          GetCertificateSerializer, GetSyllabusVersionSerializer, SyllabusVersionSerializer,
                          GetBigAcademySerializer, AcademyReportSerializer)
from .models import (Academy, AcademySpecialtyMode, SpecialtyModeTimeSlot, CohortTimeSlot, CohortUser,
                     SpecialtyMode, Cohort, Country, STUDENT, DELETED, Syllabus, SyllabusVersion)
from breathecode.authenticate.models import ProfileAcademy
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework import status
from breathecode.utils import (localize_query, capable_of, ValidationException, HeaderLimitOffsetPagination,
                               GenerateLookupsMixin)
from rest_framework.exceptions import ParseError, PermissionDenied, ValidationError

from rest_framework.decorators import renderer_classes
from rest_framework_csv import renderers as r
from rest_framework.renderers import JSONRenderer

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_timezones(request, id=None):
    # timezones = [(x, x) for x in pytz.common_timezones]
    return Response(pytz.common_timezones)


@api_view(['GET'])
def get_all_academies(request, id=None):
    items = Academy.objects.all()
    serializer = AcademySerializer(items, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_cohorts(request, id=None):

    items = Cohort.objects.filter(private=False)

    if isinstance(request.user, AnonymousUser) == False:
        # filter only to the local academy
        items = localize_query(items, request)

    upcoming = request.GET.get('upcoming', None)
    if upcoming == 'true':
        now = timezone.now()
        items = items.filter(kickoff_date__gte=now)

    academy = request.GET.get('academy', None)
    if academy is not None:
        items = items.filter(academy__slug__in=academy.split(','))

    location = request.GET.get('location', None)
    if location is not None:
        items = items.filter(academy__slug__in=location.split(','))

    sort = request.GET.get('sort', None)
    if sort is None or sort == '':
        sort = '-kickoff_date'

    items = items.order_by(sort)

    serializer = GetCohortSerializer(items, many=True)

    return Response(serializer.data)


class AcademyReportView(APIView):
    @capable_of('academy_reporting')
    def get(self, request, academy_id=None):

        academy = Academy.objects.filter(id=academy_id).first()
        if academy is None:
            raise ValidationError('Academy not found', slug='academy-not-found')

        users = AcademyReportSerializer(academy)
        return Response(users.data)


class UserMeView(APIView):
    def get(self, request, format=None):

        try:
            if isinstance(request.user, AnonymousUser):
                raise PermissionDenied('There is not user')

        except User.DoesNotExist:
            raise PermissionDenied("You don't have a user")

        users = UserMeSerializer(request.user)
        return Response(users.data)


# Create your views here.


class AcademyView(APIView):
    """
    List all snippets, or create a new snippet.
    """
    @capable_of('read_my_academy')
    def get(self, request, format=None, academy_id=None):
        item = Academy.objects.get(id=academy_id)
        serializer = GetBigAcademySerializer(item)
        return Response(serializer.data)

    @capable_of('crud_my_academy')
    def put(self, request, format=None, academy_id=None):
        academy = Academy.objects.get(id=academy_id)
        data = {}

        for key in request.data:
            data[key] = request.data.get(key)

        serializer = AcademySerializer(academy, data=data)
        if serializer.is_valid():
            serializer.save()
            # serializer = GetBigAcademySerializer(academy, data=data)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request):
        serializer = UserDJangoRestSerializer(request.user, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CohortUserView(APIView, GenerateLookupsMixin):
    """
    List all snippets, or create a new snippet.
    """
    def get(self, request, format=None):
        items = CohortUser.objects.all()

        roles = request.GET.get('roles', None)
        if roles is not None:
            items = items.filter(role__in=roles.split(','))

        finantial_status = request.GET.get('finantial_status', None)
        if finantial_status is not None:
            items = items.filter(finantial_status__in=finantial_status.split(','))

        educational_status = request.GET.get('educational_status', None)
        if educational_status is not None:
            items = items.filter(educational_status__in=educational_status.split(','))

        academy = request.GET.get('academy', None)
        if academy is not None:
            items = items.filter(cohort__academy__slug__in=academy.split(','))

        cohorts = request.GET.get('cohorts', None)
        if cohorts is not None:
            items = items.filter(cohort__slug__in=cohorts.split(','))

        users = request.GET.get('users', None)
        if users is not None:
            items = items.filter(user__id__in=users.split(','))

        serializer = GETCohortUserSerializer(items, many=True)
        return Response(serializer.data)

    def post(self, request, cohort_id=None, user_id=None):
        many = isinstance(request.data, list)
        context = {
            'request': request,
            'cohort_id': cohort_id,
            'user_id': user_id,
            'many': many,
        }

        serializer = CohortUserSerializer(data=request.data, context=context, many=many)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, cohort_id=None, user_id=None):
        many = isinstance(request.data, list)
        context = {
            'request': request,
            'cohort_id': cohort_id,
            'user_id': user_id,
            'many': many,
        }

        if not many:
            current = CohortUser.objects.filter(user__id=user_id, cohort__id=cohort_id).first()
        else:
            current = []
            index = -1
            for x in request.data:
                index = index + 1

                if 'id' in x:
                    current.append(CohortUser.objects.filter(id=x['id']).first())

                elif 'user' in x and 'cohort' in x:
                    current.append(
                        CohortUser.objects.filter(user__id=x['user'], cohort__id=x['cohort']).first())

                else:
                    raise ValidationException('Cannot determine CohortUser in ' f'index {index}')

        serializer = CohortUserPUTSerializer(current, data=request.data, context=context, many=many)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, cohort_id=None, user_id=None):
        lookups = self.generate_lookups(request, many_fields=['id'])

        if lookups and (user_id or cohort_id):
            raise ValidationException(
                'user_id or cohort_id was provided in url '
                'in bulk mode request, use querystring style instead',
                code=400)

        academy_ids = ProfileAcademy.objects.filter(user=request.user).values_list('academy__id', flat=True)

        if lookups:
            items = CohortUser.objects.filter(**lookups, cohort__academy__id__in=academy_ids)

            for item in items:
                item.delete()

            return Response(None, status=status.HTTP_204_NO_CONTENT)

        if cohort_id is None or user_id is None:
            raise ValidationException('Missing user_id or cohort_id', code=400)

        cu = CohortUser.objects.filter(user__id=user_id,
                                       cohort__id=cohort_id,
                                       cohort__academy__id__in=academy_ids).first()
        if cu is None:
            raise ValidationException('Specified cohort and user could not be found')

        cu.delete()
        return Response(None, status=status.HTTP_204_NO_CONTENT)


class AcademyCohortUserView(APIView, HeaderLimitOffsetPagination, GenerateLookupsMixin):
    """
    List all snippets, or create a new snippet.
    """
    @capable_of('read_cohort')
    def get(self, request, format=None, cohort_id=None, user_id=None, academy_id=None):
        if user_id is not None:
            item = CohortUser.objects.filter(cohort__academy__id=academy_id,
                                             user__id=user_id,
                                             cohort__id=cohort_id).first()
            if item is None:
                raise ValidationException('Cohort user not found', 404)
            serializer = GETCohortUserSerializer(item, many=False)
            return Response(serializer.data)

        items = CohortUser.objects.filter(cohort__academy__id=academy_id)

        try:
            roles = request.GET.get('roles', None)
            if roles is not None:
                items = items.filter(role__in=roles.split(','))

            finantial_status = request.GET.get('finantial_status', None)
            if finantial_status is not None:
                items = items.filter(finantial_status__in=finantial_status.split(','))

            educational_status = request.GET.get('educational_status', None)
            if educational_status is not None:
                items = items.filter(educational_status__in=educational_status.split(','))

            cohorts = request.GET.get('cohorts', None)
            if cohorts is not None:
                items = items.filter(cohort__slug__in=cohorts.split(','))

            users = request.GET.get('users', None)
            if users is not None:
                items = items.filter(user__id__in=users.split(','))

        except Exception as e:
            raise ValidationException(str(e), 400)

        page = self.paginate_queryset(items, request)
        serializer = GETCohortUserSerializer(page, many=True)

        if self.is_paginate(request):
            return self.get_paginated_response(serializer.data)
        else:
            return Response(serializer.data, status=200)

    @capable_of('crud_cohort')
    def post(self, request, cohort_id=None, academy_id=None, user_id=None):
        many = isinstance(request.data, list)
        context = {
            'request': request,
            'cohort_id': cohort_id,
            'user_id': user_id,
            'many': many,
        }

        serializer = CohortUserSerializer(data=request.data, context=context, many=many)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of('crud_cohort')
    def put(self, request, cohort_id=None, user_id=None, academy_id=None):
        many = isinstance(request.data, list)
        context = {
            'request': request,
            'cohort_id': cohort_id,
            'user_id': user_id,
            'many': many,
        }

        if not many:
            current = CohortUser.objects.filter(user__id=user_id, cohort__id=cohort_id).first()
        else:
            current = []
            index = -1
            for x in request.data:
                index = index + 1

                if 'id' in x:
                    current.append(CohortUser.objects.filter(id=x['id']).first())

                elif 'user' in x and 'cohort' in x:
                    current.append(
                        CohortUser.objects.filter(user__id=x['user'], cohort__id=x['cohort']).first())

                else:
                    raise ValidationException('Cannot determine CohortUser in ' f'index {index}')

        serializer = CohortUserPUTSerializer(current, data=request.data, context=context, many=many)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of('crud_cohort')
    def delete(self, request, cohort_id=None, user_id=None, academy_id=None):
        lookups = self.generate_lookups(request, many_fields=['id'])

        if lookups and (user_id or cohort_id):
            raise ValidationException(
                'user_id or cohort_id was provided in url '
                'in bulk mode request, use querystring style instead',
                code=400)

        if lookups:
            items = CohortUser.objects.filter(**lookups, cohort__academy__id__in=academy_id)

            for item in items:
                item.delete()

            return Response(None, status=status.HTTP_204_NO_CONTENT)

        if cohort_id is None or user_id is None:
            raise ValidationException('Missing user_id or cohort_id', code=400)

        cu = CohortUser.objects.filter(user__id=user_id,
                                       cohort__id=cohort_id,
                                       cohort__academy__id__in=academy_id).first()
        if cu is None:
            raise ValidationException('Specified cohort and user could not be found')

        cu.delete()
        return Response(None, status=status.HTTP_204_NO_CONTENT)


class AcademyCohortTimeSlotView(APIView, GenerateLookupsMixin):
    @capable_of('read_cohort')
    def get(self, request, cohort_id=None, timeslot_id=None, academy_id=None):

        if timeslot_id is not None:
            item = CohortTimeSlot.objects.filter(cohort__academy__id=academy_id,
                                                 cohort__id=cohort_id,
                                                 id=timeslot_id).first()

            if item is None:
                raise ValidationException('Time slot not found', 404, slug='time-slot-not-found')

            serializer = GETCohortTimeSlotSerializer(item, many=False)
            return Response(serializer.data)

        items = CohortTimeSlot.objects.filter(cohort__academy__id=academy_id, cohort__id=cohort_id)

        serializer = GETCohortTimeSlotSerializer(items, many=True)
        return Response(serializer.data)

    @capable_of('crud_cohort')
    def post(self, request, cohort_id=None, academy_id=None):
        if 'cohort' in request.data or 'cohort_id' in request.data:
            raise ValidationException("Cohort can't be passed in the body", 400, slug='cohort-in-body')

        cohort = Cohort.objects.filter(id=cohort_id, academy__id=academy_id).first()

        if cohort_id and not cohort:
            raise ValidationException('Cohort not found', 404, slug='cohort-not-found')

        request.data['cohort'] = cohort.id

        serializer = CohortTimeSlotSerializer(data=request.data, many=False)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of('crud_cohort')
    def put(self, request, cohort_id=None, timeslot_id=None, academy_id=None):
        if 'cohort' in request.data or 'cohort_id' in request.data:
            raise ValidationException("Cohort can't be passed in the body", 400)

        cohort = Cohort.objects.filter(id=cohort_id, academy__id=academy_id).first()

        if cohort_id and not cohort:
            raise ValidationException('Cohort not found', 404, slug='cohort-not-found')

        item = CohortTimeSlot.objects.filter(cohort__academy__id=academy_id,
                                             cohort__id=cohort_id,
                                             id=timeslot_id).first()

        if not item:
            raise ValidationException('Time slot not found', 404, slug='time-slot-not-found')

        data = {**request.data, 'id': timeslot_id, 'cohort': cohort.id}

        serializer = CohortTimeSlotSerializer(item, data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of('crud_cohort')
    def delete(self, request, cohort_id=None, timeslot_id=None, academy_id=None):
        item = CohortTimeSlot.objects.filter(cohort__academy__id=academy_id,
                                             cohort__id=cohort_id,
                                             id=timeslot_id).first()

        if not item:
            raise ValidationException('Time slot not found', 404, slug='time-slot-not-found')

        item.delete()

        return Response(None, status=status.HTTP_204_NO_CONTENT)


class AcademySyncCohortTimeSlotView(APIView, GenerateLookupsMixin):
    @capable_of('crud_certificate')
    def post(self, request, academy_id=None):
        cohort_ids = request.GET.get('cohort', '')
        if not cohort_ids:
            raise ValidationException('Missing cohort in querystring',
                                      400,
                                      slug='missing-cohort-in-querystring')

        cohort_ids = cohort_ids.split(',')
        cohorts = Cohort.objects.filter(id__in=cohort_ids)

        if len(cohorts) != len(cohort_ids):
            raise ValidationException('Cohort not found', 404, slug='cohort-not-found')

        for cohort in cohorts:
            if not cohort.specialty_mode:
                raise ValidationException("Cohort doesn't have any certificate",
                                          400,
                                          slug='cohort-without-specialty-mode')

        CohortTimeSlot.objects.filter(cohort__id__in=cohort_ids).delete()

        data = []
        for cohort in cohorts:
            certificate_id = cohort.specialty_mode.id
            certificate_timeslots = SpecialtyModeTimeSlot.objects.filter(academy__id=academy_id,
                                                                         specialty_mode__id=certificate_id)

            for certificate_timeslot in certificate_timeslots:
                data.append({
                    'cohort': cohort.id,
                    'starting_at': certificate_timeslot.starting_at,
                    'ending_at': certificate_timeslot.ending_at,
                    'recurrent': certificate_timeslot.recurrent,
                    'recurrency_type': certificate_timeslot.recurrency_type,
                })

        serializer = CohortTimeSlotSerializer(data=data, many=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AcademySpecialtyModeTimeSlotView(APIView, GenerateLookupsMixin):
    @capable_of('read_certificate')
    def get(self, request, certificate_id=None, timeslot_id=None, academy_id=None):
        if timeslot_id:
            item = SpecialtyModeTimeSlot.objects.filter(academy__id=academy_id,
                                                        specialty_mode__id=certificate_id,
                                                        id=timeslot_id).first()

            if item is None:
                raise ValidationException('Time slot not found', 404, slug='time-slot-not-found')

            serializer = GETSpecialtyModeTimeSlotSerializer(item, many=False)
            return Response(serializer.data)

        items = SpecialtyModeTimeSlot.objects.filter(academy__id=academy_id,
                                                     specialty_mode__id=certificate_id)

        serializer = GETSpecialtyModeTimeSlotSerializer(items, many=True)
        return Response(serializer.data)

    @capable_of('crud_certificate')
    def post(self, request, certificate_id=None, academy_id=None):
        if 'certificate' in request.data or 'certificate_id' in request.data:
            raise ValidationException("Certificate can't be passed is the body",
                                      400,
                                      slug='certificate-in-body')

        academy_certificate = AcademySpecialtyMode.objects.filter(specialty_mode__id=certificate_id,
                                                                  academy__id=academy_id).first()

        if certificate_id and not academy_certificate:
            raise ValidationException('Certificate not found', 404, slug='certificate-not-found')

        certificate = academy_certificate.specialty_mode

        data = {
            **request.data,
            'academy': academy_id,
            'specialty_mode': certificate.id,
        }

        serializer = SpecialtyModeTimeSlotSerializer(data=data, many=False)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of('crud_certificate')
    def put(self, request, certificate_id=None, timeslot_id=None, academy_id=None):
        if 'certificate' in request.data or 'certificate_id' in request.data:
            raise ValidationException("Certificate can't be passed is the body", 400)

        academy_certificate = AcademySpecialtyMode.objects.filter(specialty_mode__id=certificate_id,
                                                                  academy__id=academy_id).first()

        if certificate_id and not academy_certificate:
            raise ValidationException('Certificate not found', 404, slug='certificate-not-found')

        certificate = academy_certificate.specialty_mode

        item = SpecialtyModeTimeSlot.objects.filter(academy__id=academy_id,
                                                    specialty_mode__id=certificate_id,
                                                    id=timeslot_id).first()

        if not item:
            raise ValidationException('Time slot not found', 404, slug='time-slot-not-found')

        data = {
            **request.data,
            'id': timeslot_id,
            'academy': academy_id,
            'specialty_mode': certificate.id,
        }

        serializer = SpecialtyModeTimeSlotSerializer(item, data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of('crud_certificate')
    def delete(self, request, certificate_id=None, timeslot_id=None, academy_id=None):
        item = SpecialtyModeTimeSlot.objects.filter(academy__id=academy_id,
                                                    specialty_mode__id=certificate_id,
                                                    id=timeslot_id).first()

        if not item:
            raise ValidationException('Time slot not found', 404, slug='time-slot-not-found')

        item.delete()

        return Response(None, status=status.HTTP_204_NO_CONTENT)


class AcademyCohortView(APIView, HeaderLimitOffsetPagination, GenerateLookupsMixin):
    """
    List all snippets, or create a new snippet.
    """
    permission_classes = [IsAuthenticated]
    cache = CohortCache()

    @capable_of('read_cohort')
    def get(self, request, cohort_id=None, academy_id=None):
        upcoming = request.GET.get('upcoming', None)
        academy = request.GET.get('academy', None)
        location = request.GET.get('location', None)
        like = request.GET.get('like', None)
        cache_kwargs = {
            'resource': cohort_id,
            'academy_id': academy_id,
            'upcoming': upcoming,
            'academy': academy,
            'location': location,
            'like': like,
            **self.pagination_params(request),
        }

        cache = self.cache.get(**cache_kwargs)
        if cache:
            return Response(cache, status=status.HTTP_200_OK)

        if cohort_id is not None:
            item = None
            if cohort_id.isnumeric():
                item = Cohort.objects.filter(id=int(cohort_id), academy__id=academy_id).first()
            else:
                item = Cohort.objects.filter(slug=cohort_id, academy__id=academy_id).first()

            if item is None:
                return Response(status=status.HTTP_404_NOT_FOUND)

            serializer = GetCohortSerializer(item, many=False)
            return Response(serializer.data, status=status.HTTP_200_OK)

        items = Cohort.objects.filter(academy__id=academy_id)

        if upcoming == 'true':
            now = timezone.now()
            items = items.filter(kickoff_date__gte=now)

        if academy is not None:
            items = items.filter(academy__slug__in=academy.split(','))

        if location is not None:
            items = items.filter(academy__slug__in=location.split(','))

        if like is not None:
            items = items.filter(Q(name__icontains=like) | Q(slug__icontains=like))

        sort = request.GET.get('sort', None)
        if sort is None or sort == '':
            sort = '-kickoff_date'

        items = items.order_by(sort)

        page = self.paginate_queryset(items, request)
        serializer = GetCohortSerializer(page, many=True)

        if self.is_paginate(request):
            return self.get_paginated_response(serializer.data, cache=self.cache, cache_kwargs=cache_kwargs)
        else:
            self.cache.set(serializer.data, **cache_kwargs)
            return Response(serializer.data, status=status.HTTP_200_OK)

    @capable_of('crud_cohort')
    def post(self, request, academy_id=None):
        if request.data.get('academy') or request.data.get('academy_id'):
            raise ParseError(detail='academy and academy_id field is not allowed')

        academy = Academy.objects.filter(id=academy_id).first()
        if academy is None:
            raise ValidationError(f'Academy {academy_id} not found')

        syllabus = request.data.get('syllabus')
        if syllabus is None:
            raise ParseError(detail='syllabus field is missing')

        if request.data.get('current_day'):
            raise ParseError(detail='current_day field is not allowed')

        data = {
            'academy': academy,
            'current_day': 0,
        }

        for key in request.data:
            data[key] = request.data.get(key)

        if 'syllabus_version' in data:
            del data['syllabus_version']

        if 'specialty_mode' in data:
            del data['specialty_mode']

        serializer = CohortSerializer(data=data, context={"request": request, "academy": academy})
        if serializer.is_valid():
            self.cache.clear()
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of('crud_cohort')
    def put(self, request, cohort_id=None, academy_id=None):
        if request.data.get('academy') or request.data.get('academy_id'):
            raise ParseError(detail='academy and academy_id field is not allowed')

        academy = Academy.objects.filter(id=academy_id).first()
        if academy is None:
            raise ValidationError(f'Academy {academy_id} not found')

        if cohort_id is None:
            raise ValidationException('Missing cohort_id', code=400)

        cohort = Cohort.objects.filter(id=cohort_id, academy__id=academy_id)
        # only from this academy
        cohort = localize_query(cohort, request).first()
        if cohort is None:
            logger.debug(f'Cohort not be found in related academies')
            raise ValidationException('Specified cohort not be found')

        data = {}

        for key in request.data:
            data[key] = request.data.get(key)

        if 'syllabus_version' in data:
            del data['syllabus_version']

        if 'specialty_mode' in data:
            del data['specialty_mode']

        serializer = CohortPUTSerializer(cohort,
                                         data=data,
                                         context={
                                             "request": request,
                                             "cohort_id": cohort_id,
                                             "academy": academy,
                                         })
        if serializer.is_valid():
            self.cache.clear()
            serializer.save()

            serializer = GetCohortSerializer(cohort, many=False)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of('crud_cohort')
    def delete(self, request, cohort_id=None, academy_id=None):
        lookups = self.generate_lookups(request, many_fields=['id'])

        if lookups and cohort_id:
            raise ValidationException(
                'cohort_id was provided in url '
                'in bulk mode request, use querystring style instead',
                code=400)

        if lookups:
            items = Cohort.objects.filter(**lookups, academy__id=academy_id)

            for item in items:
                item_users = CohortUser.objects.filter(role=STUDENT, cohort__id=item.id)

                if item_users.count() > 0:
                    raise ValidationException('Please remove all students before trying to delete cohort',
                                              slug='cohort-has-students')

            for item in items:
                item.stage = DELETED
                item.save()

            self.cache.clear()
            return Response(None, status=status.HTTP_204_NO_CONTENT)

        if cohort_id is None:
            raise ValidationException('Missing cohort_id', code=400)

        try:
            cohort = Cohort.objects.get(id=cohort_id, academy__id=academy_id)
        except Cohort.DoesNotExist:
            raise ValidationException("Cohort doesn't exist", code=400)

        # Student
        cohort_users = CohortUser.objects.filter(role=STUDENT, cohort__id=cohort_id)

        # Check if cohort has students before deleting
        if cohort_users.count() > 0:
            raise ValidationException('Please remove all students before trying to delete cohort',
                                      slug='cohort-has-students')

        cohort.stage = DELETED
        cohort.save()

        self.cache.clear()
        return Response(None, status=status.HTTP_204_NO_CONTENT)


class CertificateAllView(APIView, HeaderLimitOffsetPagination):
    def get(self, request):
        items = SpecialtyMode.objects.all()
        page = self.paginate_queryset(items, request)
        serializer = GetCertificateSerializer(page, many=True)

        if self.is_paginate(request):
            return self.get_paginated_response(serializer.data)
        else:
            return Response(serializer.data, status=status.HTTP_200_OK)


class CertificateView(APIView, HeaderLimitOffsetPagination, GenerateLookupsMixin):
    @capable_of('read_certificate')
    def get(self, request, academy_id=None):
        cert_ids = AcademySpecialtyMode.objects.filter(academy__id=academy_id).values_list('certificate_id',
                                                                                           flat=True)
        items = SpecialtyMode.objects.filter(id__in=cert_ids)

        page = self.paginate_queryset(items, request)
        serializer = GetCertificateSerializer(page, many=True)

        if self.is_paginate(request):
            return self.get_paginated_response(serializer.data)
        else:
            return Response(serializer.data, status=status.HTTP_200_OK)

    @capable_of('crud_certificate')
    def delete(self, request, academy_id=None):
        # TODO: here i don't add one single delete, because i don't know if it is required
        lookups = self.generate_lookups(request, many_fields=['id'])

        if not lookups:
            raise ValidationException('Missing parameters in the querystring', code=400)

        ids = AcademySpecialtyMode.objects.filter(academy__id=academy_id).values_list('specialty_mode_id',
                                                                                      flat=True)
        items = SpecialtyMode.objects.filter(**lookups).filter(id__in=ids)

        for item in items:
            item.delete()

        return Response(None, status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
def get_single_course(request, certificate_slug):
    certificates = SpecialtyMode.objects.filter(slug=certificate_slug).first()
    if certificates is None:
        raise ValidationException('Certificate slug not found', code=404)
    serializer = GetCertificateSerializer(certificates, many=False)
    return Response(serializer.data, status=status.HTTP_200_OK)


class SyllabusView(APIView):
    """
    List all snippets, or create a new snippet.
    """
    @capable_of('read_syllabus')
    def get(self, request, syllabus_id=None, academy_id=None):
        if syllabus_id:
            syllabus = Syllabus.objects.filter(Q(academy_owner__id=academy_id)
                                               | Q(private=False),
                                               id=syllabus_id).first()

            if not syllabus:
                raise ValidationException('Syllabus details not found', code=404, slug='syllabus-not-found')

            serializer = GetSyllabusSerializer(syllabus, many=False)
            return Response(serializer.data, status=status.HTTP_200_OK)

        syllabus = Syllabus.objects.filter(Q(academy_owner__id=academy_id) | Q(private=False)).first()
        serializer = GetSyllabusVersionSerializer(syllabus, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @capable_of('crud_syllabus')
    def post(self, request, academy_id=None):
        academy = Academy.objects.filter(id=academy_id).first()
        data = {
            **request.data,
            'academy_owner': academy,
        }

        serializer = SyllabusSerializer(data=data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of('crud_syllabus')
    def put(self, request, syllabus_id=None, academy_id=None):
        academy = Academy.objects.filter(id=academy_id).first()
        syllabus = Syllabus.objects.filter(id=syllabus_id, academy_owner__id=academy_id).first()
        data = {
            **request.data,
            'academy_owner': academy,
        }

        if not syllabus:
            raise ValidationException('Syllabus details not found', code=404, slug='syllabus-not-found')

        serializer = SyllabusSerializer(syllabus, data=data, many=False)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SyllabusVersionView(APIView):
    """
    List all snippets, or create a new snippet.
    """
    @capable_of('read_syllabus')
    def get(self, request, certificate_slug=None, version=None, academy_id=None):
        if academy_id is None:
            raise ValidationException('Missing academy id', slug='missing-academy-id')

        certificate = SpecialtyMode.objects.filter(slug=certificate_slug)

        if not certificate:
            raise ValidationException('Certificate slug not found', code=404, slug='specialty-mode-not-found')

        certificate = certificate.filter(
            Q(syllabus__academy_owner__id=academy_id)
            | Q(syllabus__private=False)).first()

        if not certificate:
            raise ValidationException('Syllabus not found for this certificate',
                                      code=404,
                                      slug='syllabus-not-found')

        syllabus = certificate.syllabus

        if version:
            # only public syllabus or for the academy owner
            syllabus_version = SyllabusVersion.objects.filter(syllabus=syllabus, version=version).first()
            if syllabus_version is None:
                raise ValidationException('It syllabus version not found',
                                          code=404,
                                          slug='syllabus-version-not-found')

            serializer = GetSyllabusVersionSerializer(syllabus_version, many=False)
            return Response(serializer.data, status=status.HTTP_200_OK)

        # only public syllabus or for the academy owner
        syllabus_version = SyllabusVersion.objects.filter(syllabus=syllabus)
        serializer = GetSyllabusVersionSerializer(syllabus_version, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @capable_of('crud_syllabus')
    def post(self, request, certificate_slug=None, academy_id=None):
        certificate = SpecialtyMode.objects.filter(slug=certificate_slug).first()
        if certificate is None:
            raise ValidationException(f"Invalid certificate slug {certificate_slug}",
                                      code=404,
                                      slug='specialty-mode-not-found')

        if 'syllabus' not in request.data:
            raise ValidationException(f'Missing syllabus in the request', slug='missing-syllabus-in-request')

        if not Syllabus.objects.filter(id=request.data['syllabus']):
            raise ValidationException(f'Syllabus field not found', slug='syllabus-field-missing')

        academy = Academy.objects.filter(id=academy_id).first()
        if academy is None:
            raise ValidationException(f"Invalid academy {str(academy_id)}")

        serializer = SyllabusVersionSerializer(data=request.data,
                                               context={
                                                   "certificate": certificate,
                                                   "academy": academy
                                               })

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of('crud_syllabus')
    def put(self, request, certificate_slug=None, version=None, academy_id=None):
        if version is None:
            raise ValidationException('Missing syllabus version', code=400)

        certificate = SpecialtyMode.objects.filter(slug=certificate_slug).first()
        if certificate is None:
            raise ValidationException(f"Invalid certificate slug {certificate_slug}",
                                      code=404,
                                      slug='specialty-mode-not-found')

        if not certificate.syllabus:
            raise ValidationException(f"Certificate without syllabus details",
                                      code=404,
                                      slug='specialty-mode-without-syllabus')

        syllabus_version = SyllabusVersion.objects.filter(
            version=version,
            syllabus__id=certificate.syllabus.id,
            syllabus__academy_owner__id=academy_id,
        ).first()

        if not syllabus_version:
            raise ValidationException("Syllabus version not found for this academy",
                                      code=404,
                                      slug='syllabus-version-not-found')

        syllabus = syllabus_version.syllabus

        if syllabus is None:
            raise ValidationException("Syllabus not found", code=404, slug='syllabus-not-found')

        if not syllabus.specialtymode_set.filter(slug=certificate_slug).exists():
            raise ValidationException("Not exist a syllabus with this certificate",
                                      code=404,
                                      slug='certificate-not-found')

        serializer = SyllabusVersionPutSerializer(syllabus_version, data=request.data, many=False)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
