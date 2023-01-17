from email.mime import base
import hashlib, timeago, logging
import re
from rest_framework.permissions import AllowAny
from django.shortcuts import render
from django.utils import timezone
from django.db.models import Q
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect
from breathecode.authenticate.models import Token
from breathecode.mentorship.exceptions import ExtendSessionException
from breathecode.utils.api_view_extensions.api_view_extensions import APIViewExtensions
from breathecode.utils.decorators import has_permission
from breathecode.utils.views import private_view, render_message, set_query_parameter
from breathecode.utils import GenerateLookupsMixin, response_207
from breathecode.utils.multi_status_response import MultiStatusResponse
from .models import (MentorProfile, MentorshipService, MentorshipSession, MentorshipBill, SupportAgent,
                     SupportChannel)
from .forms import CloseMentoringSessionForm
from .actions import close_mentoring_session, render_session, generate_mentor_bills
from breathecode.mentorship import actions
from breathecode.notify.actions import get_template_content
from breathecode.utils.find_by_full_name import query_like_by_full_name
from .serializers import (
    GetAcademySmallSerializer,
    GETServiceSmallSerializer,
    GETSessionSmallSerializer,
    GETMentorSmallSerializer,
    MentorSerializer,
    MentorUpdateSerializer,
    SessionPUTSerializer,
    SessionSerializer,
    ServicePOSTSerializer,
    GETMentorBigSerializer,
    GETServiceBigSerializer,
    GETSessionReportSerializer,
    ServicePUTSerializer,
    BigBillSerializer,
    GETBillSmallSerializer,
    MentorshipBillPUTSerializer,
    BillSessionSerializer,
    GETMentorPublicTinySerializer,
    GETAgentSmallSerializer,
    GETSupportChannelSerializer,
)
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from breathecode.utils import capable_of, ValidationException, HeaderLimitOffsetPagination
from django.db.models import Q

logger = logging.getLogger(__name__)


# TODO: Use decorator with permissions @private_view(permission='view_mentorshipbill')
@private_view()
def render_html_bill(request, token, id=None):
    item = MentorshipBill.objects.filter(id=id).first()
    if item is None:
        return render_message(request, 'Bill not found')

    serializer = BigBillSerializer(item, many=False)
    status_map = {'DUE': 'UNDER_REVIEW', 'APPROVED': 'READY_TO_PAY', 'PAID': 'ALREADY PAID'}
    data = {
        **serializer.data,
        'status':
        status_map[serializer.data['status']],
        'title':
        f'Mentor { serializer.data["mentor"]["user"]["first_name"] } '
        f'{ serializer.data["mentor"]["user"]["last_name"] } - Invoice { item.id }',
    }
    template = get_template_content('mentorship_invoice', data)
    return HttpResponse(template['html'])


@private_view()
def forward_booking_url(request, mentor_slug, token):
    # now = timezone.now()
    if isinstance(token, HttpResponseRedirect):
        return token

    mentor = MentorProfile.objects.filter(slug=mentor_slug).first()
    if mentor is None:
        return render_message(request, f'No mentor found with slug {mentor_slug}')

    # add academy to session, will be available on html templates
    request.session['academy'] = GetAcademySmallSerializer(mentor.academy).data

    if mentor.status not in ['ACTIVE', 'UNLISTED']:
        return render_message(request, f'This mentor is not active')

    try:
        actions.mentor_is_ready(mentor)

    except Exception as e:
        logger.exception(e)
        return render_message(
            request,
            f'This mentor is not ready, please contact the mentor directly or anyone from the academy staff.')

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
def pick_mentorship_service(request, token, mentor_slug):
    base_url = request.get_full_path().split('?')[0]
    mentor = MentorProfile.objects.filter(slug=mentor_slug).first()
    if mentor is None:
        return render_message(request, f'No mentor found with slug {mentor_slug}')

    try:
        actions.mentor_is_ready(mentor)

    except Exception as e:
        logger.exception(e)
        return render_message(
            request,
            f'This mentor is not ready, please contact the mentor directly or anyone from the academy staff.')

    services = mentor.services.all()
    if not services:
        return render_message(request, f'This mentor is not available on any service')

    return render(request, 'pick_service.html', {
        'token': token.key,
        'services': services,
        'mentor': mentor,
        'baseUrl': base_url,
    })


class ForwardMeetUrl:

    def __init__(self, request, mentor_slug, service_slug, token):
        self.request = request
        self.mentor_slug = mentor_slug
        self.service_slug = service_slug
        self.token = token
        self.baseUrl = request.get_full_path()
        self.now = timezone.now()
        self.query_params = self.querystring()

        if '?' not in self.baseUrl:
            self.baseUrl += '?'

    def querystring(self):
        params = ['redirect', 'extend', 'session', 'mentee']
        result = {}

        for param in params:
            result[param] = self.request.GET.get(param, None)

        return result

    def render_pick_session(self, mentor, sessions):
        return render(
            self.request, 'pick_session.html', {
                'token': self.token.key,
                'mentor': GETMentorBigSerializer(mentor, many=False).data,
                'SUBJECT': 'Mentoring Session',
                'sessions': GETSessionReportSerializer(sessions, many=True).data,
                'baseUrl': self.baseUrl,
            })

    def render_pick_mentee(self, mentor, session):
        return render(
            self.request, 'pick_mentee.html', {
                'token': self.token.key,
                'mentor': GETMentorBigSerializer(mentor, many=False).data,
                'SUBJECT': 'Mentoring Session',
                'sessions': GETSessionReportSerializer(session, many=False).data,
                'baseUrl': self.baseUrl,
            })

    def render_end_session(self, message, btn_url):
        return render_message(
            self.request,
            message,
            btn_label='End Session',
            btn_url=btn_url,
            btn_target='_self',
        )

    def get_user_name(self, user, default):
        name = ''

        if user.first_name:
            name = user.first_name

        if user.last_name:
            name += ' ' + user.last_name

        name = re.sub(r'(\S) +(\S)', r'\1 \2', name).strip()
        if not name:
            name = default

        return name

    def render_start_session(self, session):
        student_name = self.get_user_name(session.mentee, 'student')
        mentor_name = self.get_user_name(session.mentor.user, 'a mentor')
        link = set_query_parameter('?' + self.request.GET.urlencode(), 'redirect', 'true')
        message = (f'Hello {student_name}, you are about to start a {session.service.name} '
                   f'with {mentor_name}.')

        return render(
            self.request, 'message.html', {
                'SUBJECT': 'Mentoring Session',
                'BUTTON': 'Start Session',
                'BUTTON_TARGET': '_self',
                'LINK': link,
                'MESSAGE': message,
            })

    def get_pending_sessions_or_create(self, mentor, service, mentee):
        # if specific sessions is being loaded
        if self.query_params['session'] is not None:
            sessions = MentorshipSession.objects.filter(id=self.query_params['session'])
            if sessions.count() == 0:
                return render_message(self.request,
                                      f'Session with id {self.query_params["session"]} not found')

            # set service if is null
            sessions.filter(service__isnull=True).update(service=service)
        else:
            sessions = actions.get_pending_sessions_or_create(self.token, mentor, service, mentee)
            logger.debug(f'Found {sessions.count()} sessions to close or create')

        return sessions

    def get_session(self, sessions, mentee):
        if self.query_params['session'] is not None:
            session = sessions.filter(id=self.query_params['session']).first()
        else:
            session = sessions.filter(Q(mentee=mentee) | Q(mentee__isnull=True)).first()
            # if the session.mentee is None it means the mentor had some pending unstarted session
            # if the current user is a mentee, we are going to assign that meeting to it
            if session and session.mentee is None and mentee is not None:
                session.mentee = mentee

        return session

    def __call__(self):
        if isinstance(self.token, HttpResponseRedirect):
            return self.token

        mentor = MentorProfile.objects.filter(slug=self.mentor_slug).first()
        if mentor is None:
            return render_message(self.request, f'No mentor found with slug {self.mentor_slug}')

        service = MentorshipService.objects.filter(slug=self.service_slug).first()
        if service is None:
            return render_message(self.request, f'No service found with slug {self.service_slug}')

        # add academy to session, will be available on html templates
        self.request.session['academy'] = GetAcademySmallSerializer(mentor.academy).data

        if mentor.status not in ['ACTIVE', 'UNLISTED']:
            return render_message(self.request, f'This mentor is not active at the moment')

        try:
            actions.mentor_is_ready(mentor)

        except:
            return render_message(
                self.request,
                f'This mentor is not ready, please contact the mentor directly or anyone from the academy staff.'
            )

        is_token_of_mentee = mentor.user.id != self.token.user.id

        # if the mentor is not the user, then we assume is the mentee
        mentee = self.token.user if is_token_of_mentee else None
        sessions = self.get_pending_sessions_or_create(mentor, service, mentee)

        if not is_token_of_mentee and sessions.count() > 0 and str(
                sessions.first().id) != self.query_params['session']:
            return self.render_pick_session(mentor, sessions)

        # this also set the session.mentee
        session = self.get_session(sessions, mentee)
        if session is None:
            name = self.get_user_name(mentor.user, 'the mentor')
            return render_message(self.request,
                                  f'Impossible to create or retrieve mentoring session with {name}.')

        is_mentee_params_set = bool(self.query_params['mentee'])
        is_mentee_params_undefined = self.query_params['mentee'] == 'undefined'

        # passing mentee query param
        if session.mentee is None and is_mentee_params_set and not is_mentee_params_undefined:
            session.mentee = User.objects.filter(id=self.query_params['mentee']).first()
            if session.mentee is None:
                return render_message(
                    self.request, f'Mentee with user id {self.query_params["mentee"]} was not found, '
                    f'<a href="{self.baseUrl}&mentee=undefined">click here to start the session anyway.</a>')

        # passing a invalid mentee query param
        if session.mentee is None and not is_mentee_params_undefined:
            return self.render_pick_mentee(mentor, session)

        # session ended
        if session.status not in ['PENDING', 'STARTED']:
            return render_message(
                self.request,
                f'This mentoring session has ended ({session.status}), would you like '
                f'<a href="/mentor/meet/{mentor.slug}">to start a new one?</a>.',
            )
        # Who is joining? Set meeting join in dates
        if not is_token_of_mentee:
            # only reset the joined_at it has ben more than 5min and the session has not started yey
            if session.mentor_joined_at is None or (session.started_at is None and
                                                    ((self.now - session.mentor_joined_at).seconds > 300)):
                session.mentor_joined_at = self.now

        elif self.query_params['redirect'] is not None and session.mentee.id == self.token.user.id:
            if session.started_at is None:
                session.started_at = self.now
                session.status = 'STARTED'

        # if it expired already you could extend it
        service = session.service

        session_ends_in_the_pass = session.ends_at is not None and session.ends_at < self.now
        # can extend this session?
        if session_ends_in_the_pass and (self.now -
                                         session.ends_at).total_seconds() > (service.duration.seconds / 2):
            return HttpResponseRedirect(
                redirect_to=
                f'/mentor/session/{str(session.id)}?token={self.token.key}&message=You have a session that '
                f'expired {timeago.format(session.ends_at, self.now)}. Only sessions with less than '
                f'{round(((session.service.duration.total_seconds() / 3600) * 60)/2)}min from '
                'expiration can be extended (if allowed by the academy)')

        if session_ends_in_the_pass and ((is_token_of_mentee and service.allow_mentee_to_extend) or
                                         (not is_token_of_mentee and service.allow_mentors_to_extend)):

            if self.query_params['extend'] == 'true':
                try:
                    session = actions.extend_session(session)

                except ExtendSessionException as e:
                    return self.render_end_session(
                        str(e), btn_url=f'/mentor/session/{str(session.id)}?token={self.token.key}')

            extend_url = set_query_parameter(self.request.get_full_path(), 'extend', 'true')
            return self.render_end_session(
                f'The mentoring session expired {timeago.format(session.ends_at, self.now)}: You can '
                f'<a href="{extend_url}">extend it for another 30 minutes</a> or end the session right '
                'now.',
                btn_url=f'/mentor/session/{str(session.id)}?token={self.token.key}')

        elif session_ends_in_the_pass:
            return render_message(
                self.request,
                f'The mentoring session expired {timeago.format(session.ends_at, self.now)} and it '
                'cannot be extended.',
            )

        # save progress so far, we are about to render the session below
        session.save()

        if session.mentee is None:
            return render_session(self.request, session, token=self.token)

        if self.query_params['redirect'] is not None or self.token.user.id == session.mentor.user.id:
            return render_session(self.request, session, token=self.token)

        return self.render_start_session(session)


@private_view()
def forward_meet_url(request, mentor_slug, service_slug, token):
    handler = ForwardMeetUrl(request, mentor_slug, service_slug, token)
    return handler()


@private_view()
def end_mentoring_session(request, session_id, token):
    now = timezone.now()
    if request.method == 'POST':
        _dict = request.POST.copy()
        form = CloseMentoringSessionForm(_dict)

        token_key = _dict.get('token')
        token = Token.objects.filter(key=token_key).first()
        if token is None or (token.expires_at is not None and token.expires_at < now):
            messages.error(request, 'Invalid or expired deliver token.')
            return render(request, 'form.html', {'form': form})

        session_id_from_body = _dict.get('session_id')
        session = MentorshipSession.objects.filter(id=session_id_from_body).first()
        if session is None:
            messages.error(request, 'Invalid session id.')
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
            return render_message(request, f'Session not found with id {str(session_id)}')

        # add academy to session, will be available on html templates
        request.session['academy'] = (GetAcademySmallSerializer(session.service.academy).data
                                      if session.service else None)

        # this GET request occurs when the mentor leaves the session
        session.mentor_left_at = now
        session.save()

        mentee = session.mentee

        if mentee is None:
            session.status = 'FAILED'
            session.summary = ('This session expired without assigned mentee, it probably means the mentee '
                               'never came. It will be marked as failed')
            session.save()
            pending_sessions = MentorshipSession.objects.filter(mentor__id=session.mentor.id,
                                                                status__in=['STARTED', 'PENDING'])
            return render(
                request, 'close_session.html', {
                    'token':
                    token.key,
                    'message':
                    'Previous session expired without assigned mentee, it probably means the mentee never came. It was '
                    'marked as failed. Try the mentor meeting URL again.',
                    'mentor':
                    GETMentorBigSerializer(session.mentor, many=False).data,
                    'SUBJECT':
                    'Close Mentoring Session',
                    'sessions':
                    GETSessionReportSerializer(pending_sessions, many=True).data,
                    'baseUrl':
                    request.get_full_path(),
                })

        _dict = request.GET.copy()
        _dict['token'] = request.GET.get('token', None)
        _dict['status'] = 'COMPLETED'
        _dict['summary'] = session.summary
        _dict['student_name'] = f'{mentee.first_name} {mentee.last_name}, {mentee.email}'
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


class ServiceView(APIView, HeaderLimitOffsetPagination, GenerateLookupsMixin):
    extensions = APIViewExtensions(sort='-created_at', paginate=True)

    @capable_of('read_mentorship_service')
    def get(self, request, service_id=None, academy_id=None):
        handler = self.extensions(request)

        if service_id is not None:
            service = MentorshipService.objects.filter(id=service_id, academy__id=academy_id).first()
            if service is None:
                raise ValidationException('This service does not exist on this academy',
                                          code=404,
                                          slug='not-found')

            serializer = GETServiceBigSerializer(service)
            return Response(serializer.data, status=status.HTTP_200_OK)

        items = MentorshipService.objects.filter(academy__id=academy_id)
        lookup = {}

        if 'status' in self.request.GET:
            param = self.request.GET.get('status')
            lookup['status'] = param

        name = request.GET.get('name', None)
        if name is not None:
            lookup['name__icontains'] = name
            items = items.filter(name__icontains=name)

        items = items.filter(**lookup)

        items = handler.queryset(items)
        serializer = GETServiceSmallSerializer(items, many=True)

        return handler.response(serializer.data)

    @capable_of('crud_mentorship_service')
    def post(self, request, academy_id=None):

        serializer = ServicePOSTSerializer(data=request.data,
                                           context={
                                               'request': request,
                                               'academy_id': academy_id
                                           })
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of('crud_mentorship_service')
    def put(self, request, service_id=None, academy_id=None):
        if service_id is None:
            raise ValidationException('Missing service_id')

        service = MentorshipService.objects.filter(id=service_id, academy__id=academy_id).first()
        if service is None:
            raise ValidationException('This service does not exist', code=404, slug='not-found')

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

    @capable_of('crud_event')
    def delete(self, request, academy_id=None, service_id=None):
        lookups = self.generate_lookups(request, many_fields=['id'])

        if not lookups and not service_id:
            raise ValidationException('provide arguments in the url',
                                      code=400,
                                      slug='without-lookups-and-service-id')

        if lookups and service_id:
            raise ValidationException(
                'service_id in url '
                'in bulk mode request, use querystring style instead',
                code=400,
                slug='lookups-and-session-id-together')

        if lookups:
            alls = MentorshipService.objects.filter(**lookups)
            valids = alls.filter(academy__id=academy_id)
            from_other_academy = alls.exclude(academy__id=academy_id)
            with_mentor = MentorshipService.objects.none()
            with_sessions = MentorshipService.objects.none()
            for id in lookups['id__in']:

                mentor = MentorProfile.objects.filter(academy__id=academy_id, services=id).first()
                if mentor is not None:
                    with_mentor |= MentorshipService.objects.filter(id__in=mentor.services.all())

                session = MentorshipSession.objects.filter(service=id).first()
                if session is not None:
                    with_sessions |= MentorshipService.objects.filter(id=session.service.id)

            valids = alls.exclude(
                Q(id__in=with_mentor.all()) | Q(id__in=with_sessions.all())
                | Q(id__in=from_other_academy.all()))

            responses = []
            if valids:
                responses.append(MultiStatusResponse(code=204, queryset=valids))

            if from_other_academy:
                responses.append(
                    MultiStatusResponse('Service doest not exist or does not belong to this academy',
                                        code=400,
                                        slug='not-found',
                                        queryset=from_other_academy))

            if with_mentor:
                responses.append(
                    MultiStatusResponse('Only services that are not assigned to a mentor can be deleted.',
                                        code=400,
                                        slug='service-with-mentor',
                                        queryset=with_mentor))

            if with_sessions:
                responses.append(
                    MultiStatusResponse('Only services without a session can be deleted.',
                                        code=400,
                                        slug='service-with-session',
                                        queryset=with_sessions))

            if from_other_academy or with_mentor or with_sessions:
                response = response_207(responses, 'slug')
                valids.delete()
                return response

            valids.delete()
            return Response(None, status=status.HTTP_204_NO_CONTENT)

        service = MentorshipService.objects.filter(academy__id=academy_id, id=service_id).first()
        if service is None:
            raise ValidationException('Service doest not exist or does not belong to this academy',
                                      slug='not-found')

        mentor = MentorProfile.objects.filter(academy__id=academy_id, services=service.id).first()
        if mentor is not None:
            raise ValidationException('Only services that are not assigned to a mentor can be deleted.',
                                      slug='service-with-mentor')

        session = MentorshipSession.objects.filter(service=service.id).first()

        if session is not None:
            raise ValidationException('Only services without a session can be deleted.',
                                      slug='service-with-session')

        service.delete()
        return Response(None, status=status.HTTP_204_NO_CONTENT)


class MentorView(APIView, HeaderLimitOffsetPagination):
    extensions = APIViewExtensions(sort='-created_at', paginate=True)

    @capable_of('read_mentorship_mentor')
    def get(self, request, mentor_id=None, academy_id=None):
        handler = self.extensions(request)

        if mentor_id is not None:
            mentor = MentorProfile.objects.filter(id=mentor_id, services__academy__id=academy_id).first()
            if mentor is None:
                raise ValidationException('This mentor does not exist on this academy', code=404)

            serializer = GETMentorBigSerializer(mentor)
            return Response(serializer.data, status=status.HTTP_200_OK)

        items = MentorProfile.objects.filter(academy__id=academy_id)
        lookup = {}

        if 'services' in self.request.GET:
            param = self.request.GET.get('services', '').split(',')
            lookup['services__slug__in'] = param

        if 'status' in self.request.GET:
            param = self.request.GET.get('status', 'ACTIVE')
            lookup['status__in'] = [s.strip().upper() for s in param.split(',')]

        if 'syllabus' in self.request.GET:
            param = self.request.GET.get('syllabus')
            lookup['syllabus__slug'] = param

        like = request.GET.get('like', None)
        if like is not None:
            items = query_like_by_full_name(like=like, items=items, prefix='user__')

        items = items.filter(**lookup)
        items = handler.queryset(items)
        serializer = GETMentorSmallSerializer(items, many=True)

        return handler.response(serializer.data)

    @capable_of('crud_mentorship_mentor')
    def post(self, request, academy_id=None):
        utc_now = timezone.now()

        if not 'slug' in request.data:
            raise ValidationException('Missing slug field in the request', slug='missing-slug-field')

        token = hashlib.sha1((str(request.data['slug']) + str(utc_now)).encode('UTF-8')).hexdigest()

        serializer = MentorSerializer(data={
            **request.data,
            'token': token,
            'academy': academy_id,
        })

        if serializer.is_valid():
            mentor = serializer.save()

            _serializer = GETMentorBigSerializer(mentor, many=False)
            return Response(_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of('crud_mentorship_mentor')
    def put(self, request, mentor_id=None, academy_id=None):
        if mentor_id is None:
            raise ValidationException('Missing mentor ID on the URL', 404)

        mentor = MentorProfile.objects.filter(id=mentor_id, services__academy__id=academy_id).first()
        if mentor is None:
            raise ValidationException('This mentor does not exist for this academy',
                                      code=404,
                                      slug='not-found')

        if 'user' in request.data:
            raise ValidationException('Mentor user cannot be updated, please create a new mentor instead',
                                      slug='user-read-only')

        if 'token' in request.data:
            raise ValidationException('Mentor token cannot be updated', slug='token-read-only')

        data = {}
        for key in request.data.keys():
            data[key] = request.data[key]

        serializer = MentorUpdateSerializer(mentor,
                                            data=data,
                                            context={
                                                'request': request,
                                                'academy_id': academy_id
                                            })
        if serializer.is_valid():
            mentor = serializer.save()
            _serializer = GETMentorBigSerializer(mentor)

            return Response(_serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AgentView(APIView, HeaderLimitOffsetPagination):

    extensions = APIViewExtensions(sort='-created_at', paginate=True)

    @capable_of('read_mentorship_agent')
    def get(self, request, agent_id=None, academy_id=None):
        handler = self.extensions(request)

        if agent_id is not None:
            agent = SupportAgent.objects.filter(id=agent_id, channel__academy__id=academy_id).first()
            if agent is None:
                raise ValidationException('This agent does not exist on this academy', code=404)

            serializer = GETAgentSmallSerializer(agent)
            return Response(serializer.data, status=status.HTTP_200_OK)

        items = SupportAgent.objects.filter(channel__academy__id=academy_id)
        lookup = {}

        if 'channel' in self.request.GET:
            param = self.request.GET.get('channel', '').split(',')
            lookup['channel__slug__in'] = param

        if 'status' in self.request.GET:
            param = self.request.GET.get('status', 'ACTIVE')
            lookup['status__in'] = [s.strip().upper() for s in param.split(',')]

        if 'syllabus' in self.request.GET:
            param = self.request.GET.get('syllabus')
            lookup['channel__syllabis__slug'] = param

        items = items.filter(**lookup)
        items = handler.queryset(items)
        serializer = GETAgentSmallSerializer(items, many=True)

        return handler.response(serializer.data)


class SupportChannelView(APIView, HeaderLimitOffsetPagination):

    extensions = APIViewExtensions(sort='-created_at', paginate=True)

    @capable_of('read_mentorship_agent')
    def get(self, request, supportchannel_id=None, academy_id=None):
        handler = self.extensions(request)

        if supportchannel_id is not None:
            channel = SupportChannel.objects.filter(id=supportchannel_id, academy__id=academy_id).first()
            if channel is None:
                raise ValidationException('This support channel does not exist on this academy', code=404)

            serializer = GETSupportChannelSerializer(channel)
            return Response(serializer.data, status=status.HTTP_200_OK)

        items = SupportChannel.objects.filter(academy__id=academy_id)
        lookup = {}

        if 'syllabus' in self.request.GET:
            param = self.request.GET.get('syllabus')
            lookup['syllabis__slug'] = param

        items = items.filter(**lookup)
        items = handler.queryset(items)
        serializer = GETSupportChannelSerializer(items, many=True)

        return handler.response(serializer.data)


class SessionView(APIView, HeaderLimitOffsetPagination):
    extensions = APIViewExtensions(sort='-created_at', paginate=True)

    @capable_of('read_mentorship_session')
    def get(self, request, session_id=None, academy_id=None):
        handler = self.extensions(request)

        if session_id is not None:
            session = MentorshipSession.objects.filter(id=session_id,
                                                       mentor__services__academy__id=academy_id).first()
            if session is None:
                raise ValidationException('This session does not exist on this academy',
                                          code=404,
                                          slug='not-found')

            serializer = SessionSerializer(session)
            return Response(serializer.data, status=status.HTTP_200_OK)

        items = MentorshipSession.objects.filter(mentor__services__academy__id=academy_id)
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
            if ',' in mentor or mentor.isnumeric():
                lookup['mentor__id__in'] = mentor.split(',')
            else:
                items = query_like_by_full_name(like=mentor, items=items, prefix='mentor__user__')

        mentee = request.GET.get('student', None)
        if mentee is not None:
            items = query_like_by_full_name(like=mentee, items=items, prefix='mentee__')

        service = request.GET.get('service', None)
        if service is not None:
            lookup['service__name__icontains'] = service

        items = items.filter(**lookup)
        items = handler.queryset(items)
        serializer = GETSessionSmallSerializer(items, many=True)

        return handler.response(serializer.data)

    @capable_of('crud_mentorship_session')
    def post(self, request, academy_id=None):

        serializer = SessionSerializer(data=request.data,
                                       context={
                                           'request': request,
                                           'academy_id': academy_id
                                       })
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of('crud_mentorship_session')
    def put(self, request, academy_id=None, session_id=None):

        many = isinstance(request.data, list)
        if not many:
            current = MentorshipSession.objects.filter(id=session_id,
                                                       mentor__services__academy__id=academy_id).first()
            if current is None:
                raise ValidationException('This session does not exist on this academy',
                                          code=404,
                                          slug='not-found')

            if current.bill and (current.bill.status == 'APPROVED' or current.bill.status == 'PAID'
                                 or current.bill.status == 'IGNORED'):
                raise ValidationException('Sessions associated with a closed bill cannot be edited',
                                          code=400,
                                          slug='trying-to-change-a-closed-bill')

            data = {}
            for key in request.data.keys():
                data[key] = request.data.get(key)
        else:
            data = request.data
            current = []
            index = -1
            for x in request.data:
                index = index + 1

                if 'id' not in x:
                    raise ValidationException('Cannot determine session in '
                                              f'index {index}',
                                              slug='without-id')

                instance = MentorshipSession.objects.filter(id=x['id'],
                                                            mentor__services__academy__id=academy_id).first()

                if not instance:
                    raise ValidationException(f'Session({x["id"]}) does not exist on this academy',
                                              code=404,
                                              slug='not-found')
                current.append(instance)

                if instance.bill and (instance.bill.status == 'APPROVED' or instance.bill.status == 'PAID'
                                      or instance.bill.status == 'IGNORED'):
                    raise ValidationException(
                        f'Sessions associated with a closed bill cannot be edited (index {index})',
                        code=400,
                        slug='trying-to-change-a-closed-bill')

        serializer = SessionPUTSerializer(current,
                                          data=data,
                                          context={
                                              'request': request,
                                              'academy_id': academy_id
                                          },
                                          many=many)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ServiceSessionView(APIView, HeaderLimitOffsetPagination):
    extensions = APIViewExtensions(sort='-created_at', paginate=True)

    @capable_of('read_mentorship_session')
    def get(self, request, service_id, academy_id=None):
        handler = self.extensions(request)

        if service_id is None:
            raise ValidationException('Missing service id', code=404)

        items = MentorshipSession.objects.filter(mentor__services__id=service_id,
                                                 mentor__services__academy__id=academy_id)
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

        items = items.filter(**lookup)
        items = handler.queryset(items)
        serializer = BillSessionSerializer(items, many=True)

        return handler.response(serializer.data)


class MentorSessionView(APIView, HeaderLimitOffsetPagination):
    extensions = APIViewExtensions(sort='-created_at', paginate=True)

    @capable_of('read_mentorship_session')
    def get(self, request, mentor_id, academy_id=None):
        handler = self.extensions(request)

        if mentor_id is None:
            raise ValidationException('Missing mentor id', code=404)

        items = MentorshipSession.objects.filter(mentor__id=mentor_id,
                                                 mentor__services__academy__id=academy_id)
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

        items = items.filter(**lookup)
        items = handler.queryset(items)
        serializer = BillSessionSerializer(items, many=True)

        return handler.response(serializer.data)


class BillView(APIView, HeaderLimitOffsetPagination):
    extensions = APIViewExtensions(sort='-created_at', paginate=True)

    @capable_of('read_mentorship_bill')
    def get(self, request, bill_id=None, academy_id=None):
        handler = self.extensions(request)

        if bill_id is not None:
            bill = MentorshipBill.objects.filter(id=bill_id, academy__id=academy_id).first()
            if bill is None:
                raise ValidationException('This mentorship bill does not exist on this academy',
                                          code=404,
                                          slug='not-found')

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

        items = items.filter(**lookup)
        items = handler.queryset(items)
        serializer = GETBillSmallSerializer(items, many=True)

        return handler.response(serializer.data)

    @capable_of('crud_mentorship_bill')
    def post(self, request, academy_id=None, mentor_id=None):

        if mentor_id is None:
            raise ValidationException('Missing mentor ID on the URL', code=404, slug='argument-not-provided')

        mentor = MentorProfile.objects.filter(id=mentor_id, services__academy__id=academy_id).first()
        if mentor is None:
            raise ValidationException('This mentor does not exist for this academy',
                                      code=404,
                                      slug='not-found')

        bills = generate_mentor_bills(mentor)
        serializer = GETBillSmallSerializer(bills, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @capable_of('crud_mentorship_bill')
    def put(self, request, bill_id=None, academy_id=None):
        many = isinstance(request.data, list)
        if many and bill_id:
            raise ValidationException(f'Avoid using bulk mode passing id in the url',
                                      code=404,
                                      slug='bulk-mode-and-bill-id')

        if many:
            bill = []
            for obj in request.data:
                if 'id' not in obj:
                    raise ValidationException('Bill id must be provided in bulk mode',
                                              code=404,
                                              slug='missing-some-id-in-body')

                if not (elem := MentorshipBill.objects.filter(id=obj['id']).first()):
                    raise ValidationException(f'Bill {obj["id"]} not found', code=404, slug='some-not-found')

                if elem.status == 'RECALCULATE' and 'status' in obj and obj['status'] != 'RECALCULATE':
                    raise ValidationException(
                        f'This bill must be regenerated before you can update its status',
                        code=400,
                        slug='trying-edit-status-to-dirty-bill')

                bill.append(elem)

        else:
            if bill_id is None:
                raise ValidationException('Missing bill ID on the URL',
                                          code=404,
                                          slug='without-bulk-mode-and-bill-id')

            bill = MentorshipBill.objects.filter(id=bill_id, academy__id=academy_id).first()
            if bill is None:
                raise ValidationException('This bill does not exist for this academy',
                                          code=404,
                                          slug='not-found')

            if bill.status == 'RECALCULATE' and 'status' in request.data and request.data[
                    'status'] != 'RECALCULATE':
                raise ValidationException(f'This bill must be regenerated before you can update its status',
                                          code=400,
                                          slug='trying-edit-status-to-dirty-bill')

        serializer = MentorshipBillPUTSerializer(bill,
                                                 data=request.data,
                                                 many=many,
                                                 context={
                                                     'request': request,
                                                     'academy_id': academy_id
                                                 })
        if serializer.is_valid():
            mentor = serializer.save()
            _serializer = GETBillSmallSerializer(bill, many=many)
            return Response(_serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of('crud_mentorship_bill')
    def delete(self, request, bill_id=None, academy_id=None):

        if bill_id is None:
            raise ValidationException('Missing bill ID on the URL', 404)

        bill = MentorshipBill.objects.filter(id=bill_id, academy__id=academy_id).first()
        if bill is None:
            raise ValidationException('This bill does not exist for this academy', code=404, slug='not-found')

        if bill.status == 'PAID':
            raise ValidationException('Paid bills cannot be deleted', slug='paid-bill')

        bill.delete()
        return Response(None, status=status.HTTP_204_NO_CONTENT)


class UserMeSessionView(APIView, HeaderLimitOffsetPagination):
    """
    List all snippets, or create a new snippet.
    """

    @has_permission('get_my_mentoring_sessions')
    def get(self, request):

        items = MentorshipSession.objects.filter(mentor__user__id=request.user.id)
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

        mentee = request.GET.get('mentee', None)
        if mentee is not None:
            lookup['mentee__id__in'] = mentee.split(',')

        items = items.filter(**lookup).order_by('-created_at')

        page = self.paginate_queryset(items, request)
        serializer = BillSessionSerializer(page, many=True)

        if self.is_paginate(request):
            return self.get_paginated_response(serializer.data)
        else:
            return Response(serializer.data, status=status.HTTP_200_OK)


class UserMeBillView(APIView, HeaderLimitOffsetPagination):

    @has_permission('get_my_mentoring_sessions')
    def get(self, request, bill_id=None):

        if bill_id is not None:
            bill = MentorshipBill.objects.filter(id=bill_id, mentor__user__id=request.user.id).first()
            if bill is None:
                raise ValidationException('This mentorship bill does not exist', code=404)

            serializer = BigBillSerializer(bill)
            return Response(serializer.data, status=status.HTTP_200_OK)

        items = MentorshipBill.objects.filter(mentor__user__id=request.user.id)
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

        mentee = request.GET.get('mentee', None)
        if mentee is not None:
            lookup['mentee__id__in'] = mentee.split(',')

        items = items.filter(**lookup).order_by('-created_at')
        page = self.paginate_queryset(items, request)
        serializer = GETBillSmallSerializer(page, many=True)

        if self.is_paginate(request):
            return self.get_paginated_response(serializer.data)
        else:
            return Response(serializer.data, status=status.HTTP_200_OK)


class PublicMentorView(APIView, HeaderLimitOffsetPagination):
    extensions = APIViewExtensions(sort='-created_at', paginate=True)
    permission_classes = [AllowAny]

    def get(self, request):
        handler = self.extensions(request)

        items = MentorProfile.objects.filter(status='ACTIVE')
        lookup = {}

        if 'services' in self.request.GET:
            param = self.request.GET.get('services', '').split(',')
            lookup['services__slug__in'] = param

        if 'syllabus' in self.request.GET:
            param = self.request.GET.get('syllabus')
            lookup['syllabus__slug'] = param

        items = items.filter(**lookup)
        items = handler.queryset(items)
        serializer = GETMentorPublicTinySerializer(items, many=True)

        return handler.response(serializer.data)
