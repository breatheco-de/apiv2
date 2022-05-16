import os, hashlib, timeago, logging
from django.shortcuts import render
from django.utils import timezone
from django.db.models import Q
from django.contrib.auth.models import User
from datetime import timedelta
from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect
from breathecode.admissions.models import Academy
from breathecode.authenticate.models import Token
from breathecode.utils.views import private_view, render_message, set_query_parameter
from .models import MentorProfile, MentorshipService, MentorshipSession, MentorshipBill
from .forms import CloseMentoringSessionForm
from .actions import close_mentoring_session, get_pending_sessions_or_create, render_session, generate_mentor_bills
from rest_framework import serializers
from breathecode.notify.actions import get_template_content
from rest_framework.exceptions import ValidationError, NotFound
from rest_framework.permissions import AllowAny, IsAuthenticated
from .serializers import (
    GetAcademySmallSerializer,
    GETServiceSmallSerializer,
    GETSessionSmallSerializer,
    GETMentorSmallSerializer,
    MentorSerializer,
    MentorUpdateSerializer,
    SessionSerializer,
    ServicePOSTSerializer,
    GETMentorBigSerializer,
    GETServiceBigSerializer,
    GETSessionBigSerializer,
    GETSessionReportSerializer,
    ServicePUTSerializer,
    BigBillSerializer,
    GETBillSmallSerializer,
    MentorshipBillPUTSerializer,
    BillSessionSerializer,
)
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.views import APIView
from rest_framework import status
from breathecode.utils import capable_of, ValidationException, HeaderLimitOffsetPagination, GenerateLookupsMixin
from django.db.models import Q

logger = logging.getLogger(__name__)


# TODO: Use decorator with permissions @private_view(permission='view_mentorshipbill')
@private_view()
def render_html_bill(request, token, id=None):
    item = MentorshipBill.objects.filter(id=id).first()
    if item is None:
        return render_message(request, 'Bill not found')
    else:
        serializer = BigBillSerializer(item, many=False)
        status_map = {'DUE': 'UNDER_REVIEW', 'APPROVED': 'READY_TO_PAY', 'PAID': 'ALREADY PAID'}
        data = {
            **serializer.data, 'status':
            status_map[serializer.data['status']],
            'title':
            f'Mentor { serializer.data["mentor"]["user"]["first_name"] } { serializer.data["mentor"]["user"]["last_name"] } - Invoice { item.id }'
        }
        template = get_template_content('mentorship_invoice', data)
        return HttpResponse(template['html'])


@private_view()
def forward_booking_url(request, mentor_slug, token):
    now = timezone.now()
    if isinstance(token, HttpResponseRedirect):
        return token

    mentor = MentorProfile.objects.filter(slug=mentor_slug).first()
    if mentor is None:
        return render_message(request, f'No mentor found with slug {mentor_slug}')

    # add academy to session, will be available on html templates
    request.session['academy'] = GetAcademySmallSerializer(mentor.service.academy).data

    if mentor.status not in ['ACTIVE', 'UNLISTED']:
        return render_message(request, f'This mentor is not active')

    booking_url = mentor.booking_url
    if '?' not in booking_url:
        booking_url += '?'

    return render(request, 'book_session.html', {
        'SUBJECT': 'Mentoring Session',
        'mentor': mentor,
        'mentee': token.user,
        'booking_url': booking_url,
    })


@private_view()
def forward_meet_url(request, mentor_slug, token):
    # If the ? is added at the end, everyone can asume the querystring already started
    # and its a lot easier to append variables to it
    baseUrl = request.get_full_path()
    if '?' not in baseUrl:
        baseUrl += '?'

    now = timezone.now()
    if isinstance(token, HttpResponseRedirect):
        return token

    mentee_hit_start = request.GET.get('redirect', None)
    extend = request.GET.get('extend', None)
    session_id = request.GET.get('session', None)
    mentee_id = request.GET.get('mentee', None)

    sessions = None
    mentee = None
    mentor = MentorProfile.objects.filter(slug=mentor_slug).first()
    if mentor is None:
        return render_message(request, f'No mentor found with slug {mentor_slug}')

    # add academy to session, will be available on html templates
    request.session['academy'] = GetAcademySmallSerializer(mentor.service.academy).data

    if mentor.status not in ['ACTIVE', 'UNLISTED']:
        return render_message(request, f'This mentor is not active at the moment')

    # if the mentor is not the user, then we assume is the mentee
    if mentor.user.id != token.user.id:
        mentee = token.user

    # if specific sessions is being loaded
    if session_id is not None:
        sessions = MentorshipSession.objects.filter(id=session_id)
        if sessions.count() == 0:
            return render_message(request, f'Session with id {session_id} not found')
    else:
        sessions = get_pending_sessions_or_create(token, mentor, mentee)
        logger.debug(f'Found {sessions.count()} sessions to close or create')

    logger.debug(f'Mentor: {mentor.user.id}, Session user:{token.user.id}, Mentee: {str(mentee)}')
    if mentor.user.id == token.user.id:
        logger.debug(f'With {sessions.count()} sessions and session_id {session_id}')
        if sessions.count() > 0 and (session_id is None or str(sessions.first().id) != session_id):
            return render(
                request, 'pick_session.html', {
                    'token': token.key,
                    'mentor': GETMentorBigSerializer(mentor, many=False).data,
                    'SUBJECT': 'Mentoring Session',
                    'sessions': GETSessionReportSerializer(sessions, many=True).data,
                    'baseUrl': baseUrl,
                })
    """
    From this line on, we know exactly what session is about to be opened,
    if the mentee is None it probably is a new session
    """
    logger.debug(f'Ready to render session')
    session = None
    if session_id is not None:
        session = sessions.filter(id=session_id).first()
    else:
        session = sessions.filter(mentee=mentee).first()

    if session is None:
        return render_message(request, 'Impossible to create or retrive mentoring session')

    if session.mentee is None:
        if mentee_id is not None and mentee_id != 'undefined':
            session.mentee = User.objects.filter(id=mentee_id).first()
            if session.mentee is None:
                return render_message(
                    request,
                    f'Mentee with user id {mentee_id} was not found, <a href="{baseUrl}&mentee=undefined">click here to start the session anyway.</a>'
                )

        elif mentee_id != 'undefined' and session.mentee is None:
            return render(
                request, 'pick_mentee.html', {
                    'token': token.key,
                    'mentor': GETMentorBigSerializer(mentor, many=False).data,
                    'SUBJECT': 'Mentoring Session',
                    'sessions': GETSessionReportSerializer(session, many=False).data,
                    'baseUrl': baseUrl,
                })

    if session.status not in ['PENDING', 'STARTED']:
        return render_message(
            request,
            f'This mentoring session has ended ({session.status}), would you like <a href="/mentor/meet/{mentor.slug}">to start a new one?</a>.',
        )
    # Who is joining? Set meeting joinin dates
    if mentor.user.id == token.user.id:
        # only reset the joined_at it has ben more than 5min and the session has not started yey
        if session.mentor_joined_at is None or (session.started_at is None and
                                                ((now - session.mentor_joined_at).seconds > 300)):
            session.mentor_joined_at = now
    elif mentee_hit_start is not None and session.mentee.id == token.user.id:
        if session.started_at is None:
            session.started_at = now
            session.status = 'STARTED'

    # if it expired already you could extend it
    service = session.mentor.service
    if session.ends_at is not None and session.ends_at < now:
        if (now - session.ends_at).total_seconds() > (service.duration.seconds / 2):
            return HttpResponseRedirect(
                redirect_to=
                f'/mentor/session/{str(session.id)}?token={token.key}&message=Your have a session that expired {timeago.format(session.ends_at, now)}. Only sessions with less than {round(((session.mentor.service.duration.total_seconds() / 3600) * 60)/2)}min from expiration can be extended (if allowed by the academy)'
            )

        if ((session.mentor.user.id == token.user.id and service.allow_mentors_to_extend)
                or (session.mentor.user.id != token.user.id and service.allow_mentee_to_extend)):
            if extend is True:
                session = extend_session(session)
            extend_url = set_query_parameter(request.get_full_path(), 'extend', 'true')
            return render_message(
                request,
                f'The mentoring session expired {timeago.format(session.ends_at, now)}: You can <a href="{extend_url}">extend it for another 30 minutes</a> or end the session right now.',
                btn_label='End Session',
                btn_url=f'/mentor/session/{str(session.id)}?token={token.key}',
                btn_target='_self',
            )
        else:
            return render_message(
                request,
                f'The mentoring session expired {timeago.format(session.ends_at, now)} and it cannot be extended',
            )

    # save progress so far, we are about to render the session below
    session.save()

    if session.mentee is None:
        return render_session(request, session, token=token)

    if mentee_hit_start is not None or token.user.id == session.mentor.user.id:
        return render_session(request, session, token=token)

    if session.mentor.user.first_name is None or session.mentor.user.first_name == '':
        session.mentor.user.first_name = 'a mentor.'

    return render(
        request, 'message.html', {
            'SUBJECT':
            'Mentoring Session',
            'BUTTON':
            'Start Session',
            'BUTTON_TARGET':
            '_self',
            'LINK':
            set_query_parameter('?' + request.GET.urlencode(), 'redirect', 'true'),
            'MESSAGE':
            f'Hello {session.mentee.first_name }, you are about to start a {session.mentor.service.name} with {session.mentor.user.first_name} {session.mentor.user.last_name}',
        })


@private_view()
def end_mentoring_session(request, session_id, token):
    now = timezone.now()
    if request.method == 'POST':
        _dict = request.POST.copy()
        form = CloseMentoringSessionForm(_dict)

        token = Token.objects.filter(key=_dict['token']).first()
        if token is None or (token.expires_at is not None and token.expires_at < now):
            messages.error(request, f'Invalid or expired deliver token {_dict["token"]}')
            return render(request, 'form.html', {'form': form})

        session = MentorshipSession.objects.filter(id=_dict['session_id']).first()
        if session is None:
            messages.error(request, 'Invalid session id')
            return render(request, 'form.html', {'form': form})

        if form.is_valid():
            if close_mentoring_session(session=session, data=_dict):
                pending_sessions = MentorshipSession.objects.filter(mentor__id=session.mentor.id,
                                                                    status__in=['STARTED', 'PENDING'])
                return render(
                    request, 'close_session.html', {
                        'token': token.key,
                        'message':
                        f'The mentoring session was closed successfully, you can close this window or <a href="/mentor/meet/{session.mentor.slug}?token={token.key}">go back to your meeting room.</a>',
                        'mentor': GETMentorBigSerializer(session.mentor, many=False).data,
                        'SUBJECT': 'Close Mentoring Session',
                        'sessions': GETSessionReportSerializer(pending_sessions, many=True).data,
                        'baseUrl': request.get_full_path(),
                    })
            else:
                return render_message(request, f'There was a problem ending the mentoring session')

    elif request.method == 'GET':
        session = MentorshipSession.objects.filter(id=session_id).first()
        if session is None:
            return render_message(request, f'Invalid session id {str(session_id)}')

        # add academy to session, will be available on html templates
        request.session['academy'] = GetAcademySmallSerializer(session.mentor.service.academy).data

        # this GET request occurs when the mentor leaves the session
        session.mentor_left_at = now
        session.save()

        if session.mentee is None:
            session.status = 'FAILED'
            session.summary = 'This session expired without assigned mentee, it probably means the mentee never came. It will be marked as failed'
            session.save()
            pending_sessions = MentorshipSession.objects.filter(mentor__id=session.mentor.id,
                                                                status__in=['STARTED', 'PENDING'])
            return render(
                request, 'close_session.html', {
                    'token': token.key,
                    'message':
                    'This session expired without assigned mentee, it probably means the mentee never came. It was marked as failed.',
                    'mentor': GETMentorBigSerializer(session.mentor, many=False).data,
                    'SUBJECT': 'Close Mentoring Session',
                    'sessions': GETSessionReportSerializer(pending_sessions, many=True).data,
                    'baseUrl': request.get_full_path(),
                })

        _dict = request.GET.copy()
        _dict['token'] = request.GET.get('token', None)
        _dict['status'] = 'COMPLETED'
        _dict['summary'] = session.summary
        _dict[
            'student_name'] = session.mentee.first_name + ' ' + session.mentee.last_name + ', ' + session.mentee.email
        _dict['session_id'] = session.id
        form = CloseMentoringSessionForm(_dict)

    msg = request.GET.get('message', None)
    if msg is not None and msg != '':
        messages.info(request, msg)

    return render(
        request, 'form.html', {
            'form': form,
            'disabled': session.status not in ['PENDING', 'STARTED'],
            'btn_lable': 'End Mentoring Session'
            if session.status in ['PENDING', 'STARTED'] else 'Mentoring session already ended',
            'intro': 'Please fill the following information to formally end the session',
            'title': 'End Mentoring Session'
        })


class ServiceView(APIView, HeaderLimitOffsetPagination):
    @capable_of('crud_mentorship_service')
    def post(self, request, academy_id=None):

        serializer = ServicePOSTSerializer(data=request.data,
                                           context={
                                               'request': request,
                                               'academy_id': academy_id
                                           })
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of('crud_mentorship_service')
    def put(self, request, service_id=None, academy_id=None):
        if service_id is None:
            raise ValidationException('Missing service_id')

        service = MentorshipService.objects.filter(id=service_id, academy__id=academy_id).first()
        if service is None:
            raise NotFound('This service does not exist')

        serializer = ServicePUTSerializer(service,
                                          data=request.data,
                                          context={
                                              'request': request,
                                              'academy_id': academy_id
                                          })
        if serializer.is_valid():
            serializer.save()
            serializer = GETServiceBigSerializer(service, many=False)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of('read_mentorship_service')
    def get(self, request, service_id=None, academy_id=None):

        if service_id is not None:
            service = MentorshipService.objects.filter(id=service_id, academy__id=academy_id).first()
            if service is None:
                raise NotFound('This service does not exist on this academy')

            serializer = GETServiceBigSerializer(service)
            return Response(serializer.data, status=status.HTTP_200_OK)

        items = MentorshipService.objects.filter(academy__id=academy_id)
        lookup = {}

        if 'status' in self.request.GET:
            param = self.request.GET.get('status')
            lookup['status'] = param

        items = items.filter(**lookup).order_by('-created_at')

        page = self.paginate_queryset(items, request)
        serializer = GETServiceSmallSerializer(page, many=True)

        if self.is_paginate(request):
            return self.get_paginated_response(serializer.data)
        else:
            return Response(serializer.data, status=status.HTTP_200_OK)


class MentorView(APIView, HeaderLimitOffsetPagination):
    # """
    # List all snippets, or create a new snippet.
    # """
    @capable_of('crud_mentor')
    def post(self, request, academy_id=None):

        utc_now = timezone.now()
        token = hashlib.sha1((str(request.data['slug']) + str(utc_now)).encode('UTF-8')).hexdigest()

        serializer = MentorSerializer(data={
            **request.data, 'token': token
        },
                                      context={
                                          'request': request,
                                          'academy_id': academy_id
                                      })

        if serializer.is_valid():
            mentor = serializer.save()

            _serializer = GETMentorBigSerializer(mentor, many=False)
            return Response(_serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of('crud_mentor')
    def put(self, request, mentor_id=None, academy_id=None):

        if mentor_id is None:
            raise ValidationException('Missing mentor ID on the URL', 404)

        mentor = MentorProfile.objects.filter(id=mentor_id, service__academy__id=academy_id).first()
        if mentor is None:
            raise ValidationException('This mentor does not exist for this academy', 404)

        serializer = MentorUpdateSerializer(mentor,
                                            data=request.data,
                                            context={
                                                'request': request,
                                                'academy_id': academy_id
                                            })
        if serializer.is_valid():
            mentor = serializer.save()
            _serializer = GETMentorBigSerializer(mentor)
            return Response(_serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of('read_mentorship_mentor')
    def get(self, request, mentor_id=None, academy_id=None):

        if mentor_id is not None:
            mentor = MentorProfile.objects.filter(id=mentor_id, service__academy__id=academy_id).first()
            if mentor is None:
                raise ValidationException('This mentor does not exist on this academy', code=404)

            serializer = GETMentorBigSerializer(mentor)
            return Response(serializer.data, status=status.HTTP_200_OK)

        items = MentorProfile.objects.filter(service__academy__id=academy_id)
        lookup = {}

        if 'service' in self.request.GET:
            param = self.request.GET.get('service')
            lookup['service__slug'] = param

        if 'status' in self.request.GET:
            param = self.request.GET.get('status', 'ACTIVE')
            lookup['status__in'] = [s.strip().upper() for s in param.split(',')]

        if 'syllabus' in self.request.GET:
            param = self.request.GET.get('syllabus')
            lookup['syllabus__slug'] = param

        items = items.filter(**lookup).order_by('-created_at')

        page = self.paginate_queryset(items, request)
        serializer = GETMentorSmallSerializer(page, many=True)

        if self.is_paginate(request):
            return self.get_paginated_response(serializer.data)
        else:
            return Response(serializer.data, status=status.HTTP_200_OK)


class SessionView(APIView, HeaderLimitOffsetPagination):
    """
    List all snippets, or create a new snippet.
    """
    @capable_of('crud_mentorship_session')
    def post(self, request, academy_id=None):

        serializer = SessionSerializer(data=request.data,
                                       context={
                                           'request': request,
                                           'academy_id': academy_id
                                       })
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of('read_mentorship_session')
    def get(self, request, session_id=None, academy_id=None):

        if session_id is not None:
            session = MentorshipSession.objects.filter(id=session_id,
                                                       mentor__service__academy__id=academy_id).first()
            if session is None:
                raise ValidationException('This session does not exist on this academy', code=404)

            serializer = SessionSerializer(session)
            return Response(serializer.data, status=status.HTTP_200_OK)

        items = MentorshipSession.objects.filter(mentor__service__academy__id=academy_id)
        lookup = {}

        _status = request.GET.get('status', '')
        if _status != '':
            _status = [s.strip().upper() for s in _status.split(',')]
            _status = list(filter(lambda s: s != '', _status))
            items = items.filter(status__in=_status)

        billed = request.GET.get('billed', '')
        if billed == 'true':
            items = items.filter(bill__isnull=False)
        elif billed == 'false':
            items = items.filter(bill__isnull=True)

        started_after = request.GET.get('started_after', '')
        if started_after != '':
            items = items.filter(Q(started_at__gte=started_after) | Q(started_at__isnull=True))

        ended_before = request.GET.get('ended_before', '')
        if ended_before != '':
            items = items.filter(Q(ended_at__lte=ended_before) | Q(ended_at__isnull=True))

        mentor = request.GET.get('mentor', None)
        if mentor is not None:
            lookup['mentor__id__in'] = mentor.split(',')

        items = items.filter(**lookup).order_by('-created_at')

        page = self.paginate_queryset(items, request)
        serializer = GETSessionSmallSerializer(page, many=True)

        if self.is_paginate(request):
            return self.get_paginated_response(serializer.data)
        else:
            return Response(serializer.data, status=status.HTTP_200_OK)


class ServiceSessionView(APIView, HeaderLimitOffsetPagination):
    """
    List all snippets, or create a new snippet.
    """
    @capable_of('read_mentorship_session')
    def get(self, request, service_id, academy_id=None):

        if service_id is None:
            raise ValidationException('Missing service id', code=404)

        items = MentorshipSession.objects.filter(mentor__service__id=service_id,
                                                 mentor__service__academy__id=academy_id)
        lookup = {}

        _status = request.GET.get('status', '')
        if _status != '':
            _status = [s.strip().upper() for s in _status.split(',')]
            _status = list(filter(lambda s: s != '', _status))
            items = items.filter(status__in=_status)

        billed = request.GET.get('billed', '')
        if billed == 'true':
            items = items.filter(bill__isnull=False)
        elif billed == 'false':
            items = items.filter(bill__isnull=True)

        started_after = request.GET.get('started_after', '')
        if started_after != '':
            items = items.filter(Q(started_at__gte=started_after) | Q(started_at__isnull=True))

        ended_before = request.GET.get('ended_before', '')
        if ended_before != '':
            items = items.filter(Q(ended_at__lte=ended_before) | Q(ended_at__isnull=True))

        mentor = request.GET.get('mentor', None)
        if mentor is not None:
            lookup['mentor__id__in'] = mentor.split(',')

        items = items.filter(**lookup).order_by('-created_at')

        page = self.paginate_queryset(items, request)
        serializer = BillSessionSerializer(page, many=True)

        if self.is_paginate(request):
            return self.get_paginated_response(serializer.data)
        else:
            return Response(serializer.data, status=status.HTTP_200_OK)


class MentorSessionView(APIView, HeaderLimitOffsetPagination):
    """
    List all snippets, or create a new snippet.
    """
    @capable_of('read_mentorship_session')
    def get(self, request, mentor_id, academy_id=None):

        if mentor_id is None:
            raise ValidationException('Missing mentor id', code=404)

        items = MentorshipSession.objects.filter(mentor__id=mentor_id,
                                                 mentor__service__academy__id=academy_id)
        lookup = {}

        _status = request.GET.get('status', '')
        if _status != '':
            _status = [s.strip().upper() for s in _status.split(',')]
            _status = list(filter(lambda s: s != '', _status))
            items = items.filter(status__in=_status)

        billed = request.GET.get('billed', '')
        if billed == 'true':
            items = items.filter(bill__isnull=False)
        elif billed == 'false':
            items = items.filter(bill__isnull=True)

        started_after = request.GET.get('started_after', '')
        if started_after != '':
            items = items.filter(Q(started_at__gte=started_after) | Q(started_at__isnull=True))

        ended_before = request.GET.get('ended_before', '')
        if ended_before != '':
            items = items.filter(Q(ended_at__lte=ended_before) | Q(ended_at__isnull=True))

        mentor = request.GET.get('mentor', None)
        if mentor is not None:
            lookup['mentor__id__in'] = mentor.split(',')

        items = items.filter(**lookup).order_by('-created_at')

        page = self.paginate_queryset(items, request)
        serializer = BillSessionSerializer(page, many=True)

        if self.is_paginate(request):
            return self.get_paginated_response(serializer.data)
        else:
            return Response(serializer.data, status=status.HTTP_200_OK)


class BillView(APIView, HeaderLimitOffsetPagination):
    @capable_of('read_mentorship_bill')
    def get(self, request, bill_id=None, academy_id=None):

        if bill_id is not None:
            bill = MentorshipBill.objects.filter(id=bill_id, academy__id=academy_id).first()
            if bill is None:
                raise ValidationException('This mentorhip bill does not exist on this academy', code=404)

            serializer = BigBillSerializer(bill)
            return Response(serializer.data, status=status.HTTP_200_OK)

        items = MentorshipBill.objects.filter(academy__id=academy_id)
        lookup = {}

        _status = request.GET.get('status', '')
        if _status != '':
            _status = [s.strip().upper() for s in _status.split(',')]
            _status = list(filter(lambda s: s != '', _status))
            items = items.filter(status__in=_status)

        after = request.GET.get('after', '')
        if after != '':
            items = items.filter(created_at__gte=after)

        before = request.GET.get('before', '')
        if before != '':
            items = items.filter(created_at__lte=before)

        mentor = request.GET.get('mentor', None)
        if mentor is not None:
            lookup['mentor__id__in'] = mentor.split(',')

        items = items.filter(**lookup).order_by('-created_at')
        page = self.paginate_queryset(items, request)
        serializer = GETBillSmallSerializer(page, many=True)

        if self.is_paginate(request):
            return self.get_paginated_response(serializer.data)
        else:
            return Response(serializer.data, status=status.HTTP_200_OK)

    @capable_of('read_mentorship_bill')
    def put(self, request, bill_id=None, academy_id=None):

        if bill_id is None:
            raise ValidationException('Missing bill ID on the URL', 404)

        bill = MentorshipBill.objects.filter(id=bill_id, academy__id=academy_id).first()
        if bill is None:
            raise ValidationException('This bill does not exist for this academy', 404)

        serializer = MentorshipBillPUTSerializer(bill,
                                                 data=request.data,
                                                 context={
                                                     'request': request,
                                                     'academy_id': academy_id
                                                 })
        if serializer.is_valid():
            mentor = serializer.save()
            _serializer = GETBillSmallSerializer(bill)
            return Response(_serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of('read_mentorship_bill')
    def post(self, request, academy_id=None, mentor_id=None):

        if mentor_id is None:
            raise ValidationException('Missing mentor ID on the URL', 404)

        mentor = MentorProfile.objects.filter(id=mentor_id, service__academy__id=academy_id).first()
        if mentor is None:
            raise ValidationException('This mentor does not exist for this academy', 404)

        bills = generate_mentor_bills(mentor)
        serializer = GETBillSmallSerializer(bills, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
