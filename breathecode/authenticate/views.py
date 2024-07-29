import base64
import hashlib
import logging
import os
import re
import urllib.parse
from datetime import timedelta
from urllib.parse import parse_qs, urlencode

import requests
from adrf.decorators import api_view
from adrf.views import APIView
from asgiref.sync import sync_to_async
from circuitbreaker import CircuitBreakerError
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.models import AnonymousUser, User
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect, render
from django.utils import timezone
from linked_services.django.models import AppUserAgreement
from linked_services.django.service import Service
from linked_services.rest_framework.decorators import scope
from linked_services.rest_framework.types import LinkedApp, LinkedHttpRequest, LinkedToken
from rest_framework import status
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.decorators import permission_classes
from rest_framework.exceptions import APIException, PermissionDenied, ValidationError
from rest_framework.parsers import FileUploadParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.schemas.openapi import AutoSchema

import breathecode.activity.tasks as tasks_activity
import breathecode.notify.actions as notify_actions
from breathecode.admissions.models import Academy, CohortUser, Syllabus
from breathecode.authenticate.actions import get_user_settings
from breathecode.mentorship.models import MentorProfile
from breathecode.mentorship.serializers import GETMentorSmallSerializer
from breathecode.notify.models import SlackTeam
from breathecode.services.google_cloud import FunctionV1, FunctionV2
from breathecode.utils import GenerateLookupsMixin, HeaderLimitOffsetPagination, capable_of
from breathecode.utils.api_view_extensions.api_view_extensions import APIViewExtensions
from breathecode.utils.decorators import has_permission
from breathecode.utils.find_by_full_name import query_like_by_full_name
from breathecode.utils.i18n import translation
from breathecode.utils.shorteners import C
from breathecode.utils.views import private_view, render_message, set_query_parameter
from capyc.rest_framework.exceptions import ValidationException

from .actions import (
    accept_invite,
    accept_invite_action,
    aget_user_language,
    generate_academy_token,
    get_app_url,
    get_user_language,
    resend_invite,
    reset_password,
    set_gitpod_user_expiration,
    sync_organization_members,
    update_gitpod_users,
)
from .authentication import ExpiringTokenAuthentication
from .forms import (
    InviteForm,
    LoginForm,
    PasswordChangeCustomForm,
    PickPasswordForm,
    ResetPasswordForm,
    SyncGithubUsersForm,
)
from .models import (
    AcademyAuthSettings,
    CredentialsFacebook,
    CredentialsGithub,
    CredentialsGoogle,
    CredentialsSlack,
    GithubAcademyUser,
    GitpodUser,
    Profile,
    ProfileAcademy,
    Role,
    Token,
    UserInvite,
    UserSetting,
)
from .serializers import (
    AcademyAuthSettingsSerializer,
    AppUserSerializer,
    AuthSerializer,
    AuthSettingsBigSerializer,
    GetGitpodUserSerializer,
    GetProfileAcademySerializer,
    GetProfileAcademySmallSerializer,
    GetProfileSerializer,
    GithubUserSerializer,
    GitpodUserSmallSerializer,
    MemberPOSTSerializer,
    MemberPUTSerializer,
    POSTGithubUserSerializer,
    ProfileAcademySmallSerializer,
    ProfileSerializer,
    PUTGithubUserSerializer,
    RoleBigSerializer,
    RoleSmallSerializer,
    SettingsSerializer,
    SmallAppUserAgreementSerializer,
    StudentPOSTSerializer,
    TokenSmallSerializer,
    UserInviteSerializer,
    UserInviteShortSerializer,
    UserInviteSmallSerializer,
    UserInviteWaitingListSerializer,
    UserMeSerializer,
    UserSerializer,
    UserSettingsSerializer,
    UserSmallSerializer,
    UserTinySerializer,
)

logger = logging.getLogger(__name__)

PATTERNS = {
    "CONTAINS_LOWERCASE": r"[a-z]",
    "CONTAINS_UPPERCASE": r"[A-Z]",
    "CONTAINS_SYMBOLS": r"[^a-zA-Z]",
}

PROFILE_MIME_ALLOWED = ["image/png", "image/jpeg"]


def get_profile_bucket():
    return os.getenv("PROFILE_BUCKET", "")


def get_shape_of_image_url():
    return os.getenv("GCLOUD_SHAPE_OF_IMAGE", "")


def get_google_project_id():
    return os.getenv("GOOGLE_PROJECT_ID", "")


class TemporalTokenView(ObtainAuthToken):
    schema = AutoSchema()
    permission_classes = [IsAuthenticated]

    def post(self, request):

        token_type = request.data.get("token_type", "temporal")

        allowed_token_types = ["temporal", "one_time"]
        if token_type not in allowed_token_types:
            raise ValidationException(
                f'The token type must be one of {", ".join(allowed_token_types)}',
                slug="token-type-invalid-or-not-allowed",
            )

        token, created = Token.get_or_create(user=request.user, token_type=token_type)
        return Response(
            {
                "token": token.key,
                "token_type": token.token_type,
                "expires_at": token.expires_at,
                "user_id": token.user.pk,
                "email": token.user.email,
            }
        )


class AcademyTokenView(ObtainAuthToken):
    schema = AutoSchema()
    permission_classes = [IsAuthenticated]

    @capable_of("get_academy_token")
    def get(self, request, academy_id):
        academy = Academy.objects.get(id=academy_id)
        academy_user = User.objects.filter(username=academy.slug).first()
        if academy_user is None:
            raise ValidationException("No academy token has been generated yet", slug="academy-token-not-found")

        token = Token.objects.filter(user=academy_user, token_type="permanent").first()
        if token is None:
            raise ValidationException("No academy token has been generated yet", slug="academy-token-not-found")

        return Response(
            {
                "token": token.key,
                "token_type": token.token_type,
                "expires_at": token.expires_at,
            }
        )

    @capable_of("generate_academy_token")
    def post(self, request, academy_id):

        token = generate_academy_token(academy_id, True)
        return Response(
            {
                "token": token.key,
                "token_type": token.token_type,
                "expires_at": token.expires_at,
            }
        )


class LogoutView(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        Token.objects.filter(token_type="login").delete()
        request.auth.delete()
        return Response(
            {
                "message": "User tokens successfully deleted",
            }
        )


class WaitingListView(APIView, HeaderLimitOffsetPagination, GenerateLookupsMixin):
    permission_classes = [AllowAny]

    def post(self, request):
        data = {**request.data}
        lang = get_user_language(request)

        syllabus = None
        if v := data.pop("syllabus", None):
            try:
                args = {}
                if isinstance(v, int):
                    args["id"] = v
                else:
                    args["slug"] = v

                syllabus = Syllabus.objects.filter(**args).get()

            except Exception:
                raise ValidationException(
                    translation(
                        lang, en="The syllabus does not exist", es="El syllabus no existe", slug="syllabus-not-found"
                    )
                )

        if syllabus:
            data["syllabus"] = syllabus.id

        serializer = UserInviteWaitingListSerializer(
            data=data,
            context={
                "lang": lang,
                "plan": data.get("plan"),
                "course": data.get("course"),
                "syllabus": syllabus,
            },
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):
        lang = get_user_language(request)

        invite = UserInvite.objects.filter(
            email=request.data.get("email"), status="WAITING_LIST", token=request.data.get("token", "empty")
        ).first()
        if not invite:
            raise ValidationException(
                translation(
                    lang,
                    en="The email does not exist in the waiting list",
                    es="El email no existe en la lista de espera",
                    slug="not-found",
                ),
                code=404,
            )

        data = {**request.data}

        syllabus = None
        if v := data.pop("syllabus", None):
            try:
                args = {}
                if isinstance(v, int):
                    args["id"] = v
                else:
                    args["slug"] = v

                syllabus = Syllabus.objects.filter(**args).get()

            except Exception:
                raise ValidationException(
                    translation(
                        lang, en="The syllabus does not exist", es="El syllabus no existe", slug="syllabus-not-found"
                    )
                )

        if syllabus:
            data["syllabus"] = syllabus.id

        serializer = UserInviteWaitingListSerializer(
            invite,
            data=data,
            context={
                "lang": lang,
                "plan": data.get("plan"),
                "course": data.get("course"),
                "syllabus": syllabus,
            },
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MemberView(APIView, GenerateLookupsMixin):
    extensions = APIViewExtensions(paginate=True)

    @capable_of("read_member")
    def get(self, request, academy_id, user_id_or_email=None):
        handler = self.extensions(request)

        if user_id_or_email is not None:
            item = None
            if user_id_or_email.isnumeric():
                item = ProfileAcademy.objects.filter(user__id=user_id_or_email, academy_id=academy_id).first()
            else:
                item = ProfileAcademy.objects.filter(user__email=user_id_or_email, academy_id=academy_id).first()

            if item is None:
                raise ValidationException(
                    "Profile not found for this user and academy", code=404, slug="profile-academy-not-found"
                )

            serializer = GetProfileAcademySerializer(item, many=False)
            return Response(serializer.data)

        items = ProfileAcademy.objects.filter(academy__id=academy_id)
        include = request.GET.get("include", "").split()
        if not "student" in include:
            items = items.exclude(role__slug="student")

        roles = request.GET.get("roles", "")
        if roles != "":
            items = items.filter(role__in=roles.lower().split(","))

        status = request.GET.get("status", None)
        if status is not None:
            items = items.filter(status__iexact=status)

        like = request.GET.get("like", None)
        if like is not None:
            items = query_like_by_full_name(like=like, items=items)

        items = items.exclude(user__email__contains="@token.com")

        items = handler.queryset(items)
        serializer = GetProfileAcademySmallSerializer(items, many=True)

        return handler.response(serializer.data)

    @capable_of("crud_member")
    def post(self, request, academy_id=None):
        serializer = MemberPOSTSerializer(data=request.data, context={"academy_id": academy_id, "request": request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of("crud_member")
    def put(self, request, academy_id=None, user_id_or_email=None):
        lang = get_user_language(request)

        user = ProfileAcademy.objects.filter(user__id=request.user.id, academy__id=academy_id).first()

        if user.email is None or user.email.strip() == "":
            raise ValidationException(
                translation(
                    lang,
                    en="This mentor does not have an email address",
                    es="Este mentor no tiene una dirección de correo electrónico",
                    slug="email-not-found",
                ),
                code=400,
            )

        already = None
        if user_id_or_email.isnumeric():
            already = ProfileAcademy.objects.filter(user__id=user_id_or_email, academy_id=academy_id).first()
        else:
            raise ValidationException("User id must be a numeric value", code=400, slug="user-id-is-not-numeric")

        request_data = {**request.data, "user": user_id_or_email, "academy": academy_id}
        if already:
            serializer = MemberPUTSerializer(already, data=request_data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            serializer = MemberPOSTSerializer(data=request_data, context={"academy_id": academy_id, "request": request})
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of("crud_member")
    def delete(self, request, academy_id=None, user_id_or_email=None):
        raise ValidationException(
            "This functionality is under maintenance and it's not working", code=403, slug="delete-is-forbidden"
        )


class MeInviteView(APIView, HeaderLimitOffsetPagination, GenerateLookupsMixin):

    def get(self, request):
        invites = UserInvite.objects.filter(email=request.user.email)

        status = request.GET.get("status", "")
        if status != "":
            invites = invites.filter(status__in=status.split(","))
        else:
            invites = invites.filter(status="PENDING")

        serializer = UserInviteSerializer(invites, many=True)
        return Response(serializer.data)

    def put(self, request, new_status=None):
        lookups = self.generate_lookups(request, many_fields=["id"])

        accept_invite(user=request.user)

        if new_status is None:
            raise ValidationException("Please specify new status for the invites", slug="missing-status")

        if new_status.upper() not in ["ACCEPTED", "REJECTED"]:
            raise ValidationException(f"Invalid invite status {new_status}", slug="invalid-status")

        if lookups:
            items = UserInvite.objects.filter(**lookups, email=request.user.email, status="PENDING")

            for item in items:

                item.status = new_status.upper()
                item.save()

                exists = ProfileAcademy.objects.filter(email=item.email, academy__id=item.academy.id)

                if exists.count() == 0:
                    profile_academy = ProfileAcademy(
                        academy=item.academy,
                        role=item.role,
                        status="ACTIVE",
                        email=item.email,
                        first_name=item.first_name,
                        last_name=item.last_name,
                    )
                    profile_academy.save()

                if new_status.upper() == "ACCEPTED" and User.objects.filter(email=item.email).count() == 0:
                    user = User()
                    user.email = item.email
                    user.username = item.email
                    user.first_name = item.first_name
                    user.last_name = item.last_name
                    user.save()

                serializer = UserInviteSerializer(item)
                if serializer.is_valid():
                    tasks_activity.add_activity.delay(
                        request.user.id, "invite_status_updated", related_type="auth.UserInvite", related_id=item.id
                    )

            serializer = UserInviteSerializer(items, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        else:
            raise ValidationException("Invite ids were not provided", code=400, slug="missing-ids")


class ConfirmEmailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, token=None):
        get_user_language(request)
        errors: list[C] = []

        invite = UserInvite.objects.filter(token=token).first()
        if invite is None:
            e = ValidationException("Invite not found", code=404, slug="user-invite-not-found")
            if request.META.get("HTTP_ACCEPT") == "application/json":
                raise e

            return render_message(request, e.get_message(), status=404)

        if not invite.email:
            errors.append(C("This invite don't have email, contact to admin", slug="without-email"))

        if invite.is_email_validated:
            errors.append(C("Email already validated", slug="email-already-validated"))

        if errors:
            e = ValidationException(errors, code=400)
            if request.META.get("HTTP_ACCEPT") == "application/json":
                raise e

            return render_message(request, e.get_message(), status=400, academy=invite.academy)

        invite.is_email_validated = True
        invite.save()

        if request.META.get("HTTP_ACCEPT") == "application/json":
            # If it's JSON, use your serializer and return a JSON response.
            serializer = UserInviteShortSerializer(invite, many=False)
            return Response(serializer.data)

        # If not JSON, return your HTML message.
        return render_message(request, "Your email was validated, you can close this page.", academy=invite.academy)


class ResendInviteView(APIView):
    permission_classes = [AllowAny]

    def put(self, request, invite_id=None):
        get_user_language(request)
        errors: list[C] = []

        invite = UserInvite.objects.filter(id=invite_id).first()
        if invite is None:
            raise ValidationException("Invite not found", code=404, slug="user-invite-not-found")

        invite_answered = invite.status not in ["PENDING", "WAITING_LIST"]

        if invite.is_email_validated and invite_answered:
            status = invite.status.lower()
            errors.append(C(f"You already {status} this invite", slug=f"user-already-{status}"))

        if invite.status == "WAITING_LIST":
            status = invite.status.lower()
            errors.append(C("You are in the waiting list, ", slug=f"user-already-{status}"))

        if not invite.email:
            status = invite.status.lower()
            errors.append(C("This invite don't have email, contact to admin", slug="without-email"))

        now = timezone.now()
        minutes = 10
        if invite.sent_at and invite.sent_at + timedelta(minutes=minutes) > now:
            errors.append(
                C(
                    f"You have a pending invitation sent less than {minutes} minutes ago, check your email",
                    slug=f"sent-at-diff-less-{minutes}-minutes",
                )
            )

        if errors:
            raise ValidationException(errors, code=400)

        if not invite.is_email_validated and invite_answered:
            notify_actions.send_email_message(
                "verify_email",
                invite.email,
                {
                    "SUBJECT": "Verify your 4Geeks account",
                    "LINK": os.getenv("API_URL", "") + f"/v1/auth/confirmation/{invite.token}",
                },
                academy=invite.academy,
            )

        if not invite_answered:
            resend_invite(invite.token, invite.email, invite.first_name, academy=invite.academy)

        invite.sent_at = timezone.now()
        invite.save()
        serializer = UserInviteShortSerializer(invite, many=False)
        return Response(serializer.data)


class AcademyInviteView(APIView, HeaderLimitOffsetPagination, GenerateLookupsMixin):

    @capable_of("read_invite")
    def get(self, request, academy_id=None, profileacademy_id=None, invite_id=None):

        if invite_id is not None:
            invite = UserInvite.objects.filter(academy__id=academy_id, id=invite_id, status="PENDING").first()
            if invite is None:
                raise ValidationException(
                    "No pending invite was found for this user and academy", code=404, slug="user-invite-not-found"
                )

            serializer = UserInviteSerializer(invite, many=False)
            return Response(serializer.data)

        if profileacademy_id is not None:
            profile = ProfileAcademy.objects.filter(academy__id=academy_id, id=profileacademy_id).first()
            if profile is None:
                raise ValidationException("Profile not found", code=404, slug="profile-academy-not-found")

            invite = UserInvite.objects.filter(academy__id=academy_id, email=profile.email, status="PENDING").first()

            if invite is None and profile.status != "INVITED":
                raise ValidationException(
                    "No pending invite was found for this user and academy",
                    code=404,
                    slug="user-invite-and-profile-academy-with-status-invited-not-found",
                )

            # IMPORTANT: both serializers need to include "invite_url" property to have a consistent response
            if invite is not None:
                serializer = UserInviteSerializer(invite, many=False)
                return Response(serializer.data)

            if profile.status == "INVITED":
                serializer = GetProfileAcademySerializer(profile, many=False)
                return Response(serializer.data)

        invites = UserInvite.objects.filter(academy__id=academy_id)

        status = request.GET.get("status", "")
        if status != "":
            invites = invites.filter(status__in=status.split(","))
        else:
            invites = invites.filter(status="PENDING")

        if "role" in self.request.GET:
            param = self.request.GET.get("role")
            invites = invites.filter(role__name__icontains=param)

        like = request.GET.get("like", None)
        if like is not None:
            invites = query_like_by_full_name(like=like, items=invites)

        invites = invites.order_by(request.GET.get("sort", "-created_at"))

        page = self.paginate_queryset(invites, request)
        serializer = UserInviteSerializer(page, many=True)

        if self.is_paginate(request):
            return self.get_paginated_response(serializer.data)
        else:
            return Response(serializer.data, status=200)

    @capable_of("crud_invite")
    def delete(self, request, academy_id=None):
        lookups = self.generate_lookups(request, many_fields=["id"])
        if lookups:
            items = UserInvite.objects.filter(**lookups, academy__id=academy_id)

            for item in items:
                item.delete()
            return Response(None, status=status.HTTP_204_NO_CONTENT)
        else:
            raise ValidationException("Invite ids were not provided", 404, slug="missing_ids")

    @capable_of("invite_resend")
    def put(self, request, invite_id=None, profileacademy_id=None, academy_id=None):
        invite = None
        profile_academy = None
        if invite_id is not None:
            invite = UserInvite.objects.filter(academy__id=academy_id, id=invite_id, status="PENDING").first()
            if invite is None:
                raise ValidationException(
                    "No pending invite was found for this user and academy", code=404, slug="user-invite-not-found"
                )

        elif profileacademy_id is not None:
            profile_academy = ProfileAcademy.objects.filter(id=profileacademy_id).first()

            if profile_academy is None:
                raise ValidationException("Member not found", code=400, slug="profile-academy-not-found")

            invite = UserInvite.objects.filter(academy__id=academy_id, email=profile_academy.email).first()

        if (
            invite is None
            and profile_academy is not None
            and profile_academy.status == "INVITED"
            and (profile_academy.user.email or invite.email)
        ):
            notify_actions.send_email_message(
                "academy_invite",
                profile_academy.user.email or invite.email,
                {
                    "subject": f"Invitation to study at {profile_academy.academy.name}",
                    "invites": [ProfileAcademySmallSerializer(profile_academy).data],
                    "user": UserSmallSerializer(profile_academy.user).data,
                    "LINK": os.getenv("API_URL") + "/v1/auth/academy/html/invite",
                },
                academy=profile_academy.academy,
            )
            serializer = GetProfileAcademySerializer(profile_academy)
            return Response(serializer.data)

        if invite is None:
            raise ValidationException("Invite not found", code=400, slug="user-invite-not-found")

        if invite.sent_at is not None:
            now = timezone.now()
            minutes_diff = (now - invite.sent_at).total_seconds() / 60.0

            if minutes_diff < 2:
                raise ValidationException(
                    "Impossible to resend invitation", code=400, slug="sent-at-diff-less-two-minutes"
                )

        email = (profile_academy and profile_academy.user and profile_academy.user.email) or invite.email
        if not email:
            raise ValidationException("Impossible to determine the email of user", code=400, slug="without-email")

        resend_invite(invite.token, email, invite.first_name, academy=invite.academy)

        invite.sent_at = timezone.now()
        invite.save()
        serializer = UserInviteSerializer(invite, many=False)
        return Response(serializer.data)


class StudentView(APIView, GenerateLookupsMixin):
    extensions = APIViewExtensions(paginate=True, sort="-created_at")

    @capable_of("read_student")
    def get(self, request, academy_id=None, user_id_or_email=None):
        handler = self.extensions(request)

        if user_id_or_email is not None:
            profile = None
            if user_id_or_email.isnumeric():
                profile = ProfileAcademy.objects.filter(academy__id=academy_id, user__id=user_id_or_email).first()
            else:
                profile = ProfileAcademy.objects.filter(academy__id=academy_id, user__email=user_id_or_email).first()

            if profile is None:
                raise ValidationException("Profile not found", code=404, slug="profile-academy-not-found")

            serializer = GetProfileAcademySerializer(profile, many=False)
            return Response(serializer.data)

        items = ProfileAcademy.objects.filter(role__slug="student", academy__id=academy_id)

        like = request.GET.get("like", None)
        if like is not None:
            items = query_like_by_full_name(like=like, items=items)

        status = request.GET.get("status", None)
        if status is not None:
            items = items.filter(status__iexact=status)

        cohort = request.GET.get("cohort", None)
        if cohort is not None:
            lookups = self.generate_lookups(request, many_fields=["cohort"])
            items = items.filter(user__cohortuser__cohort__slug__in=lookups["cohort__in"])

        items = handler.queryset(items)
        serializer = GetProfileAcademySmallSerializer(items, many=True)

        return handler.response(serializer.data)

    @capable_of("crud_student")
    def post(self, request, academy_id=None):

        serializer = StudentPOSTSerializer(data=request.data, context={"academy_id": academy_id, "request": request})

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of("crud_student")
    def put(self, request, academy_id=None, user_id_or_email=None):
        if not user_id_or_email.isnumeric():
            raise ValidationException("User id must be a numeric value", code=404, slug="user-id-is-not-numeric")

        student = ProfileAcademy.objects.filter(user__id=user_id_or_email, academy__id=academy_id).first()

        if student and student.role.slug != "student":
            raise ValidationException(
                f"This endpoint can only update student profiles (not {student.role.slug})",
                code=400,
                slug="trying-to-change-a-staff",
            )

        request_data = {**request.data, "user": user_id_or_email, "academy": academy_id, "role": "student"}
        if "role" in request.data:
            raise ValidationException(
                "The student role cannot be updated with this endpoint, user /member instead.",
                code=400,
                slug="trying-to-change-role",
            )

        if not student:
            raise ValidationException(
                "The user is not a student in this academy", code=404, slug="profile-academy-not-found"
            )

        serializer = MemberPUTSerializer(student, data=request_data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of("crud_student")
    def delete(self, request, academy_id=None, user_id_or_email=None):
        raise ValidationException(
            "This functionality is under maintenance and it's not working", code=403, slug="delete-is-forbidden"
        )


class LoginView(ObtainAuthToken):
    schema = AutoSchema()

    def post(self, request, *args, **kwargs):

        serializer = AuthSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token, created = Token.get_or_create(user=user, token_type="login")

        tasks_activity.add_activity.delay(user.id, "login", related_type="auth.User", related_id=user.id)

        return Response({"token": token.key, "user_id": user.pk, "email": user.email, "expires_at": token.expires_at})


@api_view(["GET"])
@permission_classes([AllowAny])
def get_token_info(request, token):

    token = Token.objects.filter(key=token).first()

    if token is None or token.expires_at < timezone.now():
        raise PermissionDenied("Expired or invalid token")

    return Response(
        {"token": token.key, "token_type": token.token_type, "expires_at": token.expires_at, "user_id": token.user.pk}
    )


class UserMeView(APIView):

    def get(self, request, format=None):
        # TODO: This should be not accessible because this endpoint require auth
        try:
            if isinstance(request.user, AnonymousUser):
                raise ValidationException("There is not user", slug="without-auth", code=403)

        except User.DoesNotExist:
            raise ValidationException("You don't have a user", slug="user-not-found", code=403)

        users = UserSerializer(request.user)
        return Response(users.data)

    def put(self, request):
        # TODO: This should be not accessible because this endpoint require auth
        try:
            if isinstance(request.user, AnonymousUser):
                raise ValidationException("There is not user", slug="without-auth", code=403)

        except User.DoesNotExist:
            raise ValidationException("You don't have a user", slug="user-not-found", code=403)

        serializer = UserMeSerializer(request.user, data=request.data, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserSettingsView(APIView):

    def get(self, request, format=None):
        try:
            if isinstance(request.user, AnonymousUser):
                raise ValidationException("There is not user", slug="without-auth", code=403)

        except User.DoesNotExist:
            raise ValidationException("You don't have a user", slug="user-not-found", code=403)

        settings = get_user_settings(request.user.id)
        serializer = SettingsSerializer(settings)
        return Response(serializer.data)

    def put(self, request):
        try:
            if isinstance(request.user, AnonymousUser):
                raise ValidationException("Invalid or unauthenticated user", slug="without-auth", code=403)

        except User.DoesNotExist:
            raise ValidationException("You don't have a user", slug="user-not-found", code=403)

        settings, created = UserSetting.objects.get_or_create(user_id=request.user.id)

        serializer = UserSettingsSerializer(settings, data=request.data, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Create your views here.


@api_view(["GET"])
def get_users(request):

    query = User.objects.all()

    def find_user_by_name(query_name, qs):
        for term in query_name.split():
            qs = qs.filter(Q(first_name__icontains=term) | Q(last_name__icontains=term))
        return qs

    name = request.GET.get("name", None)
    if name is not None:
        query = find_user_by_name(name, query)

    like = request.GET.get("like", None)
    if like is not None:
        if "@" in like:
            query = query.filter(Q(email__icontains=like))
        else:
            query = find_user_by_name(like, query)

    query = query.exclude(email__contains="@token.com")
    query = query.order_by("-date_joined")
    users = UserSmallSerializer(query, many=True)
    return Response(users.data)


@api_view(["GET"])
def get_user_by_id_or_email(request, id_or_email):

    query = None
    if id_or_email.isnumeric():
        query = User.objects.filter(id=id_or_email).first()
    else:
        query = User.objects.filter(email=id_or_email).first()

    if query is None:
        raise ValidationException("User with that id or email does not exists", slug="user-dont-exists", code=404)

    users = UserSmallSerializer(query, many=False)
    return Response(users.data)


@api_view(["GET"])
@permission_classes([AllowAny])
def get_roles(request, role_slug=None):

    if role_slug is not None:
        role = Role.objects.filter(slug=role_slug).first()
        if role is None:
            raise ValidationException("Role not found", code=404)

        serializer = RoleBigSerializer(role)
        return Response(serializer.data)

    queryset = Role.objects.all()
    serializer = RoleSmallSerializer(queryset, many=True)
    return Response(serializer.data)


# Create your views here.


@api_view(["GET"])
@permission_classes([AllowAny])
def get_github_token(request, token=None):

    url = request.query_params.get("url", None)
    if url == None:
        raise ValidationException("No callback URL specified", slug="no-callback-url")

    if token is not None:
        if Token.get_valid(token) is None:
            raise ValidationException("Invalid or missing token", slug="invalid-token")
        else:
            url = url + f"&user={token}"

    scope = request.query_params.get("scope", "user repo read:org admin:org")
    try:
        scope = base64.b64decode(scope.encode("utf-8")).decode("utf-8")
    except Exception:
        pass

    params = {
        "client_id": os.getenv("GITHUB_CLIENT_ID", ""),
        "redirect_uri": os.getenv("GITHUB_REDIRECT_URL", "") + f"?url={url}",
        "scope": scope,
    }

    logger.debug("Redirecting to github")
    logger.debug(params)

    redirect = f"https://github.com/login/oauth/authorize?{urlencode(params)}"

    if settings.DEBUG:
        return HttpResponse(f"Redirect to: <a href='{redirect}'>{redirect}</a>")
    else:
        return HttpResponseRedirect(redirect_to=redirect)


# Create your views here.


@api_view(["GET"])
@permission_classes([AllowAny])
def save_github_token(request):

    logger.debug("Github callback just landed")
    logger.debug(request.query_params)

    error = request.query_params.get("error", False)
    error_description = request.query_params.get("error_description", "")
    if error:
        raise APIException("Github: " + error_description)

    url = request.query_params.get("url", None)
    if url == None:
        raise ValidationException("No callback URL specified", slug="no-callback-url")

    # the url may or may not be encoded
    try:
        url = base64.b64decode(url.encode("utf-8")).decode("utf-8")
    except Exception:
        pass

    code = request.query_params.get("code", None)
    if code == None:
        raise ValidationException("No github code specified", slug="no-code")

    token = request.query_params.get("user", None)

    payload = {
        "client_id": os.getenv("GITHUB_CLIENT_ID", ""),
        "client_secret": os.getenv("GITHUB_SECRET", ""),
        "redirect_uri": os.getenv("GITHUB_REDIRECT_URL", ""),
        "code": code,
    }
    headers = {"Accept": "application/json"}
    resp = requests.post("https://github.com/login/oauth/access_token", data=payload, headers=headers, timeout=2)
    if resp.status_code == 200:

        logger.debug("Github responded with 200")

        body = resp.json()
        if "access_token" not in body:
            raise APIException(body["error_description"])

        github_token = body["access_token"]
        resp = requests.get(
            "https://api.github.com/user", headers={"Authorization": "token " + github_token}, timeout=2
        )
        if resp.status_code == 200:
            github_user = resp.json()
            logger.debug(github_user)

            if github_user["email"] is None:
                resp = requests.get(
                    "https://api.github.com/user/emails", headers={"Authorization": "token " + github_token}, timeout=2
                )
                if resp.status_code == 200:
                    emails = resp.json()
                    primary_emails = [x for x in emails if x["primary"] == True]
                    if len(primary_emails) > 0:
                        github_user["email"] = primary_emails[0]["email"]
                    elif len(emails) > 0:
                        github_user["email"] = emails[0]["email"]

            if github_user["email"] is None:
                raise ValidationError("Impossible to retrieve user email")

            user = None  # assuming by default that its a new user
            # is a valid token??? if not valid it will become None
            if token is not None and token != "":
                token = Token.get_valid(token)
                if not token:
                    logger.debug("Token not found or is expired")
                    raise ValidationException(
                        "Token was not found or is expired, please use a different token",
                        code=404,
                        slug="token-not-found",
                    )
                user = User.objects.filter(auth_token=token.id).first()
            else:
                # for the token to become null for easier management
                token = None

            # user can't be found thru token, lets try thru the github credentials
            if token is None and user is None:
                user = User.objects.filter(credentialsgithub__github_id=github_user["id"]).first()
                if user is None:
                    user = User.objects.filter(
                        email__iexact=github_user["email"], credentialsgithub__isnull=True
                    ).first()

            user_does_not_exists = user is None
            if user_does_not_exists:
                invite = UserInvite.objects.filter(status="WAITING_LIST", email=github_user["email"]).first()

            if user_does_not_exists and invite:
                if url is None or url == "":
                    url = get_app_url()

                return render_message(
                    request,
                    f"You are still number {invite.id} on the waiting list, we will email you once you are "
                    f'given access <a href="{url}">Back to 4Geeks.com</a>',
                    academy=invite.academy,
                )

            if user_does_not_exists:
                academy = None
                if invite:
                    academy = invite.academy

                return render_message(
                    request,
                    "We could not find in our records the email associated to this github account, "
                    'perhaps you want to signup to the platform first? <a href="' + url + '">Back to 4Geeks.com</a>',
                    academy=academy,
                )

            github_credentials = CredentialsGithub.objects.filter(github_id=github_user["id"]).first()

            # update latest credentials if the user.id doesn't match
            if github_credentials and github_credentials.user.id != user.id:
                github_credentials.delete()
                github_credentials = None

            # create a new credentials if it doesn't exists
            if github_credentials is None:
                github_credentials = CredentialsGithub(github_id=github_user["id"], user=user)

            github_credentials.token = github_token
            github_credentials.username = github_user["login"]
            github_credentials.email = github_user["email"].lower()
            github_credentials.avatar_url = github_user["avatar_url"]
            github_credentials.name = github_user["name"]
            github_credentials.blog = github_user["blog"]
            github_credentials.bio = github_user["bio"]
            github_credentials.company = github_user["company"]
            github_credentials.twitter_username = github_user["twitter_username"]
            github_credentials.save()

            # IMPORTANT! The GithubAcademyUser.username is used for billing purposes on the provisioning activity, we have
            # to keep it in sync when the user autenticate's with github
            GithubAcademyUser.objects.filter(user=user).update(username=github_credentials.username)

            profile = Profile.objects.filter(user=user).first()
            if profile is None:
                profile = Profile(
                    user=user,
                    avatar_url=github_user["avatar_url"],
                    blog=github_user["blog"],
                    bio=github_user["bio"],
                    twitter_username=github_user["twitter_username"],
                )
                profile.save()

            if not profile.avatar_url:
                profile.avatar_url = github_user["avatar_url"]
                profile.save()

            student_role = Role.objects.get(slug="student")
            cus = CohortUser.objects.filter(user=user, role="STUDENT")
            for cu in cus:
                profile_academy = ProfileAcademy.objects.filter(user=cu.user, academy=cu.cohort.academy).first()
                if profile_academy is None:
                    profile_academy = ProfileAcademy(
                        user=cu.user,
                        academy=cu.cohort.academy,
                        role=student_role,
                        email=cu.user.email,
                        first_name=cu.user.first_name,
                        last_name=cu.user.last_name,
                        status="ACTIVE",
                    )
                    profile_academy.save()

            if not token:
                token, created = Token.get_or_create(user=user, token_type="login")

            # register user in rigobot
            rigobot_payload = {"organization": "4geeks", "user_token": token.key}
            headers = {"Content-Type": "application/json"}
            rigobot_resp = requests.post(
                "https://rigobot.herokuapp.com/v1/auth/invite", timeout=2, headers=headers, json=rigobot_payload
            )

            if rigobot_resp.status_code == 200:
                logger.debug("User registered on rigobot")
            else:
                logger.error("Failed user registration on rigobot")

            return HttpResponseRedirect(redirect_to=url + "?token=" + token.key)

        else:
            raise APIException("Error from github")


# Create your views here.
@api_view(["GET"])
@permission_classes([AllowAny])
def get_slack_token(request):
    """Generate stack redirect url for authorize."""
    url = request.query_params.get("url", None)
    if url is None:
        raise ValidationError("No callback URL specified")

    # the url may or may not be encoded
    try:
        url = base64.b64decode(url.encode("utf-8")).decode("utf-8")
    except Exception:
        pass

    user_id = request.query_params.get("user", None)
    if user_id is None:
        raise ValidationError("No user specified on the URL")

    academy = request.query_params.get("a", None)
    if academy is None:
        raise ValidationError("No academy specified on the URL")

    # Missing scopes!! admin.invites:write, identify
    scopes = (
        "app_mentions:read",
        "channels:history",
        "channels:join",
        "channels:read",
        "chat:write",
        "chat:write.customize",
        "commands",
        "files:read",
        "files:write",
        "groups:history",
        "groups:read",
        "groups:write",
        "incoming-webhook",
        "team:read",
        "users:read",
        "users:read.email",
        "users.profile:read",
        "users:read",
    )

    query_string = f"a={academy}&url={url}&user={user_id}".encode("utf-8")
    payload = str(base64.urlsafe_b64encode(query_string), "utf-8")
    params = {
        "client_id": os.getenv("SLACK_CLIENT_ID", ""),
        "redirect_uri": os.getenv("SLACK_REDIRECT_URL", "") + "?payload=" + payload,
        "scope": ",".join(scopes),
    }
    redirect = "https://slack.com/oauth/v2/authorize?"
    for key in params:
        redirect += f"{key}={params[key]}&"

    if settings.DEBUG:
        return HttpResponse(f"Redirect to: <a href='{redirect}'>{redirect}</a>")
    else:
        return HttpResponseRedirect(redirect_to=redirect)


# Create your views here.


@api_view(["GET"])
@permission_classes([AllowAny])
def save_slack_token(request):
    """Get Slack token and redirect to authorization route."""
    logger.debug("Slack callback just landed")

    error = request.query_params.get("error", False)
    error_description = request.query_params.get("error_description", "")
    if error:
        raise APIException("Slack: " + error_description)

    original_payload = request.query_params.get("payload", None)
    payload = request.query_params.get("payload", None)
    if payload is None:
        raise ValidationError("No payload specified")
    else:
        try:
            payload = base64.b64decode(payload).decode("utf-8")
            payload = parse_qs(payload)
        except Exception:
            raise ValidationError("Cannot decode payload in base64")

    if "url" not in payload:
        logger.exception(payload)
        raise ValidationError("No url specified from the slack payload")

    if "user" not in payload:
        logger.exception(payload)
        raise ValidationError("No user id specified from the slack payload")

    if "a" not in payload:
        logger.exception(payload)
        raise ValidationError("No academy id specified from the slack payload")

    try:
        academy = Academy.objects.get(id=payload["a"][0])
    except Exception as e:
        raise ValidationError("Not exist academy with that id") from e

    user = None
    try:
        user = User.objects.get(id=payload["user"][0])
    except Exception as e:
        raise ValidationError("Not exist user with that id") from e

    code = request.query_params.get("code", None)
    if code is None:
        raise ValidationError("No slack code specified")

    params = {
        "client_id": os.getenv("SLACK_CLIENT_ID", ""),
        "client_secret": os.getenv("SLACK_SECRET", ""),
        "redirect_uri": os.getenv("SLACK_REDIRECT_URL", "") + "?payload=" + original_payload,
        "code": code,
    }
    resp = requests.post("https://slack.com/api/oauth.v2.access", data=params, timeout=2)
    if resp.status_code == 200:

        logger.debug("Slack responded with 200")

        slack_data = resp.json()
        if "access_token" not in slack_data:
            raise APIException("Slack error status: " + slack_data["error"])

        slack_data = resp.json()
        logger.debug(slack_data)

        # delete all previous credentials for the same team and cohort
        CredentialsSlack.objects.filter(
            app_id=slack_data["app_id"], team_id=slack_data["team"]["id"], user__id=user.id
        ).delete()
        credentials = CredentialsSlack(
            user=user,
            app_id=slack_data["app_id"],
            bot_user_id=slack_data["bot_user_id"],
            token=slack_data["access_token"],
            team_id=slack_data["team"]["id"],
            team_name=slack_data["team"]["name"],
            authed_user=slack_data["authed_user"]["id"],
        )
        credentials.save()

        team = SlackTeam.objects.filter(academy__id=academy.id, slack_id=slack_data["team"]["id"]).first()
        if team is None:
            team = SlackTeam(slack_id=slack_data["team"]["id"], owner=user, academy=academy)

        team.name = slack_data["team"]["name"]
        team.save()

        return HttpResponseRedirect(redirect_to=payload["url"][0])


# Create your views here.
@api_view(["GET"])
@permission_classes([AllowAny])
def get_facebook_token(request):
    """Generate stack redirect url for authorize."""
    url = request.query_params.get("url", None)
    if url is None:
        raise ValidationError("No callback URL specified")

    # the url may or may not be encoded
    try:
        url = base64.b64decode(url.encode("utf-8")).decode("utf-8")
    except Exception:
        pass

    user_id = request.query_params.get("user", None)
    if user_id is None:
        raise ValidationError("No user specified on the URL")

    academy = request.query_params.get("a", None)
    if academy is None:
        raise ValidationError("No academy specified on the URL")

    # Missing scopes!! admin.invites:write, identify
    scopes = (
        "email",
        "ads_read",
        "business_management",
        "leads_retrieval",
        "pages_manage_metadata",
        "pages_read_engagement",
    )
    query_string = f"a={academy}&url={url}&user={user_id}".encode("utf-8")
    payload = str(base64.urlsafe_b64encode(query_string), "utf-8")
    params = {
        "client_id": os.getenv("FACEBOOK_CLIENT_ID", ""),
        "redirect_uri": os.getenv("FACEBOOK_REDIRECT_URL", ""),
        "scope": ",".join(scopes),
        "state": payload,
    }
    redirect = "https://www.facebook.com/v8.0/dialog/oauth?"
    for key in params:
        redirect += f"{key}={params[key]}&"

    if settings.DEBUG:
        return HttpResponse(f"Redirect to: <a href='{redirect}'>{redirect}</a>")
    else:
        return HttpResponseRedirect(redirect_to=redirect)


# Create your views here.
@api_view(["GET"])
@permission_classes([AllowAny])
def save_facebook_token(request):
    """Save facebook token."""
    logger.debug("Facebook callback just landed")
    error = request.query_params.get("error_code", False)
    error_description = request.query_params.get("error_message", "")
    if error:
        raise APIException("Facebook: " + error_description)

    payload = request.query_params.get("state", None)
    if payload is None:
        raise ValidationError("No payload specified")
    else:
        try:
            payload = base64.b64decode(payload).decode("utf-8")
            payload = parse_qs(payload)
        except Exception:
            raise ValidationError("Cannot decode payload in base64")

    if "url" not in payload:
        logger.exception(payload)
        raise ValidationError("No url specified from the slack payload")

    if "user" not in payload:
        logger.exception(payload)
        raise ValidationError("No user id specified from the slack payload")

    if "a" not in payload:
        logger.exception(payload)
        raise ValidationError("No academy id specified from the slack payload")

    try:
        academy = Academy.objects.get(id=payload["a"][0])
    except Exception as e:
        raise ValidationError("Not exist academy with that id") from e

    try:
        user = User.objects.get(id=payload["user"][0])
    except Exception as e:
        raise ValidationError("Not exist user with that id") from e

    # token = request.query_params.get('token', None)
    # if token == None:
    #     raise ValidationError("No facebook token specified")

    code = request.query_params.get("code", None)
    if code is None:
        raise ValidationError("No slack code specified")

    params = {
        "client_id": os.getenv("FACEBOOK_CLIENT_ID", ""),
        "client_secret": os.getenv("FACEBOOK_SECRET", ""),
        "redirect_uri": os.getenv("FACEBOOK_REDIRECT_URL", ""),
        "code": code,
    }
    resp = requests.post("https://graph.facebook.com/v8.0/oauth/access_token", data=params, timeout=2)
    if resp.status_code == 200:

        logger.debug("Facebook responded with 200")

        facebook_data = resp.json()
        if "access_token" not in facebook_data:
            logger.debug("Facebook response body")
            logger.debug(facebook_data)
            raise APIException("Facebook error status: " + facebook_data["error_message"])

        # delete all previous credentials for the same team
        CredentialsFacebook.objects.filter(user_id=user.id).delete()

        utc_now = timezone.now()
        expires_at = utc_now + timezone.timedelta(milliseconds=facebook_data["expires_in"])

        credentials = CredentialsFacebook(
            user=user,
            academy=academy,
            expires_at=expires_at,
            token=facebook_data["access_token"],
        )
        credentials.save()

        params = {
            "access_token": facebook_data["access_token"],
            "fields": "id,email",
        }
        resp = requests.post("https://graph.facebook.com/me", data=params, timeout=2)
        if resp.status_code == 200:
            logger.debug("Facebook responded with 200")
            facebook_data = resp.json()
            if "email" in facebook_data:
                credentials.email = facebook_data["email"]
            if "id" in facebook_data:
                credentials.facebook_id = facebook_data["id"]
            credentials.save()

        return HttpResponseRedirect(redirect_to=payload["url"][0])


def change_password(request, token):
    if request.method == "POST":
        form = PasswordChangeCustomForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Important!
            messages.success(request, "Your password was successfully updated!")
            return redirect("change_password")
        else:
            messages.error(request, "Please correct the error below.")
    else:
        form = PasswordChangeCustomForm(request.user)
    return render(request, "form.html", {"form": form})


class TokenTemporalView(APIView):

    @capable_of("generate_temporal_token")
    def post(self, request, profile_academy_id=None, academy_id=None):
        profile_academy = ProfileAcademy.objects.filter(id=profile_academy_id).first()
        if profile_academy is None:
            raise ValidationException("Member not found", code=404, slug="member-not-found")

        token, created = Token.get_or_create(user=profile_academy.user, token_type="temporal")
        serializer = TokenSmallSerializer(token)
        return Response(serializer.data)


def sync_gitpod_users_view(request):

    if request.method == "POST":
        _dict = request.POST.copy()
        form = SyncGithubUsersForm(_dict)

        if "html" not in _dict or _dict["html"] == "":
            messages.error(request, "HTML string is required")
            return render(request, "form.html", {"form": form})

        try:
            all_usernames = update_gitpod_users(_dict["html"])
            return render(
                request,
                "message.html",
                {
                    "MESSAGE": f'{len(all_usernames["active"])} active and {len(all_usernames["inactive"])} inactive users found'
                },
            )
        except Exception as e:
            return render_message(request, str(e))

    else:
        form = SyncGithubUsersForm()
    return render(request, "form.html", {"form": form})


def reset_password_view(request):

    if request.method == "POST":
        _dict = request.POST.copy()
        form = PickPasswordForm(_dict)

        if "email" not in _dict or _dict["email"] == "":
            messages.error(request, "Email is required")
            return render(request, "form.html", {"form": form})

        users = User.objects.filter(email__iexact=_dict["email"])
        if users.count() > 0:
            reset_password(users)
        else:
            logger.debug("No users with " + _dict["email"] + " email to reset password")

        if "callback" in _dict and _dict["callback"] != "":
            return HttpResponseRedirect(redirect_to=_dict["callback"] + "?msg=Check your email for a password reset!")
        else:
            return render(request, "message.html", {"MESSAGE": "Check your email for a password reset!"})
    else:
        _dict = request.GET.copy()
        _dict["callback"] = request.GET.get("callback", "")
        form = ResetPasswordForm(_dict)
        return render(request, "form.html", {"form": form})


def pick_password(request, token):
    _dict = request.POST.copy()
    _dict["token"] = token
    _dict["callback"] = request.GET.get("callback", "")

    token_instance = Token.get_valid(token)
    invite = None

    # allow a token to change the password
    if token_instance:
        user = token_instance.user

    # allow a invite token to change the password
    else:
        invite = UserInvite.objects.filter(token=token).first()

        # just can process if this user not have a password yet
        user = User.objects.filter(email=invite.email, password="").first() if invite else None

    if not user:
        academy = None
        if invite:
            academy = invite.academy
        return render_message(request, "The link has expired.", academy=academy)

    form = PickPasswordForm(_dict)
    if request.method == "POST":
        password1 = request.POST.get("password1", None)
        password2 = request.POST.get("password2", None)

        if password1 != password2:
            obj = {}
            if invite and invite.academy:
                obj["COMPANY_INFO_EMAIL"] = invite.academy.feedback_email
                obj["COMPANY_LEGAL_NAME"] = invite.academy.legal_name or invite.academy.name
                obj["COMPANY_LOGO"] = invite.academy.logo_url
                obj["COMPANY_NAME"] = invite.academy.name

                if "heading" not in obj:
                    obj["heading"] = invite.academy.name

            messages.error(request, "Passwords don't match")
            return render(request, "form.html", {"form": form, **obj})

        if not password1:
            obj = {}
            if invite and invite.academy:
                obj["COMPANY_INFO_EMAIL"] = invite.academy.feedback_email
                obj["COMPANY_LEGAL_NAME"] = invite.academy.legal_name or invite.academy.name
                obj["COMPANY_LOGO"] = invite.academy.logo_url
                obj["COMPANY_NAME"] = invite.academy.name

                if "heading" not in obj:
                    obj["heading"] = invite.academy.name

            messages.error(request, "Password can't be empty")
            return render(request, "form.html", {"form": form, **obj})

        if (
            len(password1) < 8
            or not re.findall(PATTERNS["CONTAINS_LOWERCASE"], password1)
            or not re.findall(PATTERNS["CONTAINS_UPPERCASE"], password1)
            or not re.findall(PATTERNS["CONTAINS_SYMBOLS"], password1)
        ):
            obj = {}
            if invite and invite.academy:
                obj["COMPANY_INFO_EMAIL"] = invite.academy.feedback_email
                obj["COMPANY_LEGAL_NAME"] = invite.academy.legal_name or invite.academy.name
                obj["COMPANY_LOGO"] = invite.academy.logo_url
                obj["COMPANY_NAME"] = invite.academy.name

                if "heading" not in obj:
                    obj["heading"] = invite.academy.name

            messages.error(request, "Password must contain 8 characters with lowercase, uppercase and " "symbols")
            return render(request, "form.html", {"form": form, **obj})

        else:
            user.set_password(password1)
            user.save()

            # destroy the token
            if token_instance:
                token_instance.delete()

            UserInvite.objects.filter(email=user.email, is_email_validated=False).update(is_email_validated=True)

            callback = request.POST.get("callback", None)
            if callback is not None and callback != "":
                return HttpResponseRedirect(redirect_to=request.POST.get("callback"))
            else:
                obj = {}
                if invite and invite.academy:
                    obj["COMPANY_INFO_EMAIL"] = invite.academy.feedback_email
                    obj["COMPANY_LEGAL_NAME"] = invite.academy.legal_name or invite.academy.name
                    obj["COMPANY_LOGO"] = invite.academy.logo_url
                    obj["COMPANY_NAME"] = invite.academy.name

                    if "heading" not in obj:
                        obj["heading"] = invite.academy.name

                return render(
                    request,
                    "message.html",
                    {
                        "MESSAGE": "You password has been successfully set.",
                        "BUTTON": "Continue to sign in",
                        "BUTTON_TARGET": "_self",
                        "LINK": os.getenv("APP_URL", "https://4geeks.com") + "/login",
                        **obj,
                    },
                )

    return render(request, "form.html", {"form": form})


class PasswordResetView(APIView):

    @capable_of("send_reset_password")
    def post(self, request, profileacademy_id=None, academy_id=None):

        profile_academy = ProfileAcademy.objects.filter(id=profileacademy_id).first()
        if profile_academy is None:
            raise ValidationException("Member not found", 400)

        if reset_password([profile_academy.user], academy=profile_academy.academy):

            token = Token.objects.filter(user=profile_academy.user, token_type="temporal").first()
            serializer = TokenSmallSerializer(token)
            return Response(serializer.data)
        else:
            raise ValidationException("Reset password token could not be sent")


class ProfileInviteMeView(APIView):

    def get(self, request):
        invites = UserInvite.objects.filter(email=request.user.email)
        profile_academies = ProfileAcademy.objects.filter(user=request.user, status="INVITED")
        mentor_profiles = MentorProfile.objects.filter(user=request.user, status="INVITED")

        return Response(
            {
                "invites": UserInviteSerializer(invites, many=True).data,
                "profile_academies": GetProfileAcademySerializer(profile_academies, many=True).data,
                "mentor_profiles": GETMentorSmallSerializer(mentor_profiles, many=True).data,
            }
        )


@private_view()
def render_user_invite(request, token):
    accepting = request.GET.get("accepting", "")
    rejecting = request.GET.get("rejecting", "")
    if accepting.strip() != "":
        accept_invite(accepting, token.user)

    if rejecting.strip() != "":
        UserInvite.objects.filter(id__in=rejecting.split(","), email=token.user.email, status="PENDING").update(
            status="REJECTED"
        )

    pending_invites = UserInvite.objects.filter(email=token.user.email, status="PENDING")
    if pending_invites.count() == 0:
        return render_message(
            request, "You don't have any more pending invites", btn_label="Continue to 4Geeks", btn_url=get_app_url()
        )

    querystr = urllib.parse.urlencode({"callback": get_app_url(), "token": token.key})
    url = os.getenv("API_URL") + "/v1/auth/member/invite?" + querystr
    return render(
        request,
        "user_invite.html",
        {
            "subject": "Invitation to study at 4Geeks.com",
            "invites": UserInviteSmallSerializer(pending_invites, many=True).data,
            "LINK": url,
            "user": UserTinySerializer(token.user, many=False).data,
        },
    )


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def render_invite(request, token, member_id=None):
    _dict = request.POST.copy()
    _dict["token"] = token
    _dict["callback"] = request.GET.get("callback", "")

    lang = get_user_language(request)

    invite = UserInvite.objects.filter(token=token).first()
    if invite is None or invite.status != "PENDING":
        callback_msg = ""
        if _dict["callback"] != "":
            callback_msg = (
                ". You can try and login at <a href='" + _dict["callback"] + "'>" + _dict["callback"] + "</a>"
            )

        academy = None
        if invite and invite.academy:
            academy = invite.academy

        return render_message(
            request, "Invitation not found or it was already accepted" + callback_msg, academy=academy
        )

    if request.method == "GET" and request.META.get("CONTENT_TYPE") == "application/json":
        serializer = UserInviteSerializer(invite, many=False)
        return Response(serializer.data)

    if request.method == "GET":

        if invite and User.objects.filter(email=invite.email).exists():
            redirect = os.getenv("API_URL") + "/v1/auth/member/invite"
            return HttpResponseRedirect(redirect_to=redirect)

        form = InviteForm(
            {
                "callback": [""],
                **_dict,
                "first_name": invite.first_name,
                "last_name": invite.last_name,
                "phone": invite.phone,
            }
        )

        obj = {}
        if invite and invite.academy:
            obj["COMPANY_INFO_EMAIL"] = invite.academy.feedback_email
            obj["COMPANY_LEGAL_NAME"] = invite.academy.legal_name or invite.academy.name
            obj["COMPANY_LOGO"] = invite.academy.logo_url
            obj["COMPANY_NAME"] = invite.academy.name

            if "heading" not in obj:
                obj["heading"] = invite.academy.name

        return render(
            request,
            "form_invite.html",
            {
                "form": form,
                **obj,
            },
        )

    if request.method == "POST" and request.META.get("CONTENT_TYPE") == "application/json":
        _dict = request.data
        _dict["token"] = token
        _dict["callback"] = request.GET.get("callback", "")

        try:
            invite = accept_invite_action(_dict, token, lang)
        except Exception as e:
            raise ValidationException(str(e))

        serializer = UserInviteShortSerializer(invite, many=False)
        return Response(serializer.data)

    if request.method == "POST":
        try:
            accept_invite_action(_dict, token, lang)
        except Exception as e:
            form = InviteForm(_dict)
            messages.error(request, str(e))

            obj = {}
            if invite and invite.academy:
                obj["COMPANY_INFO_EMAIL"] = invite.academy.feedback_email
                obj["COMPANY_LEGAL_NAME"] = invite.academy.legal_name or invite.academy.name
                obj["COMPANY_LOGO"] = invite.academy.logo_url
                obj["COMPANY_NAME"] = invite.academy.name

                if "heading" not in obj:
                    obj["heading"] = invite.academy.name

            return render(
                request,
                "form_invite.html",
                {
                    "form": form,
                    **obj,
                },
            )

        callback = request.POST.get("callback", None)
        if callback:
            uri = callback[0] if isinstance(callback, list) else callback
            if len(uri) > 0 and uri[0] == "[":
                uri = uri[2:-2]
            if settings.DEBUG:
                return HttpResponse(f"Redirect to: <a href='{uri}'>{uri}</a>")
            else:
                return HttpResponseRedirect(redirect_to=uri)
        else:
            obj = {}
            if invite and invite.academy:
                obj["COMPANY_INFO_EMAIL"] = invite.academy.feedback_email
                obj["COMPANY_LEGAL_NAME"] = invite.academy.legal_name or invite.academy.name
                obj["COMPANY_LOGO"] = invite.academy.logo_url
                obj["COMPANY_NAME"] = invite.academy.name

                if "heading" not in obj:
                    obj["heading"] = invite.academy.name

            return render(
                request,
                "message.html",
                {
                    "MESSAGE": "Welcome to 4Geeks, you can go ahead and log in",
                    **obj,
                },
            )


@private_view()
def render_academy_invite(request, token):
    accepting = request.GET.get("accepting", "")
    rejecting = request.GET.get("rejecting", "")
    if accepting.strip() != "":
        ProfileAcademy.objects.filter(id__in=accepting.split(","), user__id=token.user.id, status="INVITED").update(
            status="ACTIVE"
        )
    if rejecting.strip() != "":
        ProfileAcademy.objects.filter(id__in=rejecting.split(","), user__id=token.user.id).delete()

    pending_invites = ProfileAcademy.objects.filter(user__id=token.user.id, status="INVITED")
    if pending_invites.count() == 0:
        return render_message(
            request, "You don't have any more pending invites", btn_label="Continue to 4Geeks", btn_url=get_app_url()
        )

    querystr = urllib.parse.urlencode({"callback": get_app_url(), "token": token.key})
    url = os.getenv("API_URL") + "/v1/auth/academy/html/invite?" + querystr
    return render(
        request,
        "academy_invite.html",
        {
            "subject": "Invitation to study at 4Geeks.com",
            "invites": ProfileAcademySmallSerializer(pending_invites, many=True).data,
            "LINK": url,
            "user": UserTinySerializer(token.user, many=False).data,
        },
    )


def login_html_view(request):

    _dict = request.GET.copy()
    form = LoginForm(_dict)

    if request.method == "POST":

        try:

            url = request.POST.get("url", None)
            if url is None or url == "":
                raise Exception("Invalid redirect url, you must specify a url to redirect to")

            # the url may or may not be encoded
            try:
                url = base64.b64decode(url.encode("utf-8")).decode("utf-8")
            except Exception:
                pass

            email = request.POST.get("email", None)
            password = request.POST.get("password", None)

            user = None
            if email and password:
                user = User.objects.filter(Q(email=email.lower()) | Q(username=email)).first()
                if not user:
                    msg = "Unable to log in with provided credentials."
                    raise Exception(msg)
                if user.check_password(password) != True:
                    msg = "Unable to log in with provided credentials."
                    raise Exception(msg)
                # The authenticate call simply returns None for is_active=False
                # users. (Assuming the default ModelBackend authentication
                # backend.)
            else:
                msg = 'Must include "username" and "password".'
                raise Exception(msg, code=403)

            if (
                user
                and not UserInvite.objects.filter(
                    email__iexact=email, status="ACCEPTED", is_email_validated=True
                ).exists()
            ):
                raise Exception("You need to validate your email first")

            token, _ = Token.get_or_create(user=user, token_type="login")

            request.session["token"] = token.key
            return HttpResponseRedirect(
                set_query_parameter(set_query_parameter(url, "attempt", "1"), "token", str(token))
            )

        except Exception as e:
            messages.error(request, e.message if hasattr(e, "message") else e)
            return render(request, "login.html", {"form": form})
    else:
        url = request.GET.get("url", None)
        if url is None or url == "":
            messages.error(request, "You must specify a 'url' (querystring) to redirect to after successful login")

    return render(request, "login.html", {"form": form, "redirect_url": request.GET.get("url", None)})


@api_view(["GET"])
@permission_classes([AllowAny])
def get_google_token(request, token=None):

    if token == None:
        raise ValidationException("No session token has been specified", slug="no-session-token")

    url = request.query_params.get("url", None)
    if url == None:
        raise ValidationException("No callback URL specified", slug="no-callback-url")

    try:
        url = base64.b64decode(url.encode("utf-8")).decode("utf-8")
    except Exception:
        pass

    token = Token.get_valid(token)  # IMPORTANT!! you can only connect to google with temporal short lasting tokens
    if token is None or token.token_type != "temporal":
        raise ValidationException("Invalid or inactive token", code=403, slug="invalid-token")

    params = {
        "response_type": "code",
        "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
        "redirect_uri": os.getenv("GOOGLE_REDIRECT_URL", ""),
        "access_type": "offline",  # we need offline access to receive refresh token and avoid total expiration
        "scope": "https://www.googleapis.com/auth/calendar.events",
        "state": f"token={token.key}&url={url}",
    }

    logger.debug("Redirecting to google")
    logger.debug(params)

    redirect = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

    if settings.DEBUG:
        return HttpResponse(f"Redirect to: <a href='{redirect}'>{redirect}</a>")
    else:
        return HttpResponseRedirect(redirect_to=redirect)


# Create your views here.


@api_view(["GET"])
@permission_classes([AllowAny])
def save_google_token(request):

    logger.debug("Google callback just landed")
    logger.debug(request.query_params)

    error = request.query_params.get("error", False)
    error_description = request.query_params.get("error_description", "")
    if error:
        raise APIException("Google OAuth: " + error_description)

    state = parse_qs(request.query_params.get("state", None))

    if state["url"] == None:
        raise ValidationException("No callback URL specified", slug="no-callback-url")
    if state["token"] == None:
        raise ValidationException("No user token specified", slug="no-user-token")

    code = request.query_params.get("code", None)
    if code == None:
        raise ValidationException("No google code specified", slug="no-code")

    payload = {
        "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
        "client_secret": os.getenv("GOOGLE_SECRET", ""),
        "redirect_uri": os.getenv("GOOGLE_REDIRECT_URL", ""),
        "grant_type": "authorization_code",
        "code": code,
    }
    headers = {"Accept": "application/json"}
    resp = requests.post("https://oauth2.googleapis.com/token", data=payload, headers=headers, timeout=2)
    if resp.status_code == 200:

        logger.debug("Google responded with 200")

        body = resp.json()
        if "access_token" not in body:
            raise APIException(body["error_description"])

        logger.debug(body)

        token = Token.get_valid(state["token"][0])
        if not token:
            logger.debug(f'Token {state["token"][0]} not found or is expired')
            raise ValidationException(
                "Token was not found or is expired, please use a different token", code=404, slug="token-not-found"
            )

        user = token.user
        refresh = ""
        if "refresh_token" in body:
            refresh = body["refresh_token"]

        CredentialsGoogle.objects.filter(user__id=user.id).delete()
        google_credentials = CredentialsGoogle(
            user=user,
            token=body["access_token"],
            refresh_token=refresh,
            expires_at=timezone.now() + timedelta(seconds=body["expires_in"]),
        )
        google_credentials.save()

        return HttpResponseRedirect(redirect_to=state["url"][0] + "?token=" + token.key)

    else:
        logger.error(resp.json())
        raise APIException("Error from google credentials")


class GithubUserView(APIView, GenerateLookupsMixin):
    extensions = APIViewExtensions(paginate=True)

    @capable_of("get_github_user")
    def get(self, request, academy_id, githubuser_id=None):
        handler = self.extensions(request)

        if githubuser_id is not None:
            item = GithubAcademyUser.objects.filter(id=githubuser_id, academy_id=academy_id).first()
            if item is None:
                raise ValidationException(
                    "Github User not found for this academy", code=404, slug="githubuser-not-found"
                )

            serializer = GithubUserSerializer(item, many=False)
            return Response(serializer.data)

        items = GithubAcademyUser.objects.filter(Q(academy__id=academy_id) | Q(academy__isnull=True))

        like = request.GET.get("like", None)
        if like is not None:
            items = items.filter(
                Q(username__icontains=like)
                | Q(user__email__icontains=like)
                | Q(user__first_name__icontains=like)
                | Q(user__last_name__icontains=like)
            )

        items = items.order_by(request.GET.get("sort", "-created_at"))

        items = handler.queryset(items)
        serializer = GithubUserSerializer(items, many=True)

        return handler.response(serializer.data)

    @capable_of("update_github_user")
    def put(self, request, academy_id, githubuser_id=None):
        lookups = self.generate_lookups(request, many_fields=["id"])
        if githubuser_id is not None:
            lookups = {"id": githubuser_id}

        if lookups is None or len(lookups.keys()) == 0:
            raise ValidationException("No github users lookups to find", code=404, slug="no-lookup")

        items = GithubAcademyUser.objects.filter(**lookups, academy_id=academy_id)
        if items.count() == 0:
            raise ValidationException("Github User not found for this academy", code=404, slug="githubuser-not-found")

        valid = []
        for gu in items:
            serializer = PUTGithubUserSerializer(gu, data=request.data)
            if serializer.is_valid():
                valid.append(serializer)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data_list = []
        for serializer in valid:
            _item = serializer.save()
            data_list.append(_item)

        if githubuser_id is None:
            return Response(GithubUserSerializer(data_list, many=True).data, status=status.HTTP_200_OK)
        else:
            return Response(GithubUserSerializer(data_list[0], many=False).data, status=status.HTTP_200_OK)

    @capable_of("update_github_user")
    def post(self, request, academy_id):

        body = request.data
        if "cohort" not in body:
            raise ValidationException(
                translation(
                    en="You must specify the cohort the user belongs to, and it must be active on it",
                    es="Debes especificar la cohort y el usuario debe estar activo en ella",
                ),
                slug="user-not-found",
            )
        if "user" not in body:
            raise ValidationException(
                translation(en="You must specify the user", es="Debes especificar el usuario"), slug="user-not-found"
            )

        cu = CohortUser.objects.filter(user=body["user"], cohort=body["cohort"], educational_status="ACTIVE").first()
        if cu is None:
            raise ValidationException(
                translation(
                    en="You must specify the cohort the user belongs to, and it must be active on it",
                    es="Debes especificar la cohort y el usuario debe estar activo en ella",
                ),
                slug="cohort-not-found",
            )

        context = {"academy_id": academy_id, "request": request}
        serializer = POSTGithubUserSerializer(data=request.data, context=context)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AcademyGithubSyncView(APIView, GenerateLookupsMixin):
    extensions = APIViewExtensions(paginate=True)

    @capable_of("sync_organization_users")
    def put(self, request, academy_id):

        settings = AcademyAuthSettings.objects.filter(academy__id=academy_id).first()
        if settings is None:
            raise ValidationException(
                translation(
                    en="Github Settings not found for this academy",
                    es="No se ha encontrado una configuracion para esta academy en Github",
                ),
                slug="settings-not-found",
            )

        if not settings.github_is_sync:
            raise ValidationException(
                translation(
                    en="Github sync is turned off in the academy settings",
                    es="La sincronización con github esta desactivada para esta academia",
                ),
                slug="github-sync-off",
            )

        try:
            result = sync_organization_members(academy_id)
        except Exception as e:
            raise ValidationException(str(e))

        _status = status.HTTP_200_OK if result else status.HTTP_400_BAD_REQUEST
        return Response(None, status=_status)


class AcademyAuthSettingsView(APIView, GenerateLookupsMixin):

    @capable_of("get_academy_auth_settings")
    def get(self, request, academy_id):
        lang = get_user_language(request)

        settings = AcademyAuthSettings.objects.filter(academy_id=academy_id).first()
        if settings is None:
            raise ValidationException(
                translation(
                    lang,
                    en="Academy has not github authentication settings",
                    es="La academia no tiene configurada la integracion con github",
                    slug="no-github-auth-settings",
                )
            )

        serializer = AuthSettingsBigSerializer(settings, many=False)
        return Response(serializer.data)

    @capable_of("crud_academy_auth_settings")
    def put(self, request, academy_id):
        settings = AcademyAuthSettings.objects.filter(academy_id=academy_id).first()
        context = {"academy_id": academy_id, "request": request}
        if settings is None:
            serializer = AcademyAuthSettingsSerializer(data=request.data, context=context)
        else:
            serializer = AcademyAuthSettingsSerializer(settings, data=request.data, context=context)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GitpodUserView(APIView, GenerateLookupsMixin):
    extensions = APIViewExtensions(paginate=True)

    @capable_of("get_gitpod_user")
    def get(self, request, academy_id, gitpoduser_id=None):
        handler = self.extensions(request)

        if gitpoduser_id is not None:
            item = GitpodUser.objects.filter(id=gitpoduser_id, academy_id=academy_id).first()
            if item is None:
                raise ValidationException(
                    "Gitpod User not found for this academy", code=404, slug="gitpoduser-not-found"
                )

            serializer = GetGitpodUserSerializer(item, many=False)
            return Response(serializer.data)

        items = GitpodUser.objects.filter(Q(academy__id=academy_id) | Q(academy__isnull=True))

        like = request.GET.get("like", None)
        if like is not None:
            items = items.filter(
                Q(github_username__icontains=like)
                | Q(user__email__icontains=like)
                | Q(user__first_name__icontains=like)
                | Q(user__last_name__icontains=like)
            )

        items = items.order_by(request.GET.get("sort", "expires_at"))

        items = handler.queryset(items)
        serializer = GitpodUserSmallSerializer(items, many=True)

        return handler.response(serializer.data)

    @capable_of("update_gitpod_user")
    def put(self, request, academy_id, gitpoduser_id):

        item = GitpodUser.objects.filter(id=gitpoduser_id, academy_id=academy_id).first()
        if item is None:
            raise ValidationException("Gitpod User not found for this academy", code=404, slug="gitpoduser-not-found")

        if request.data is None or ("expires_at" in request.data and request.data["expires_at"] is None):
            item.expires_at = None
            item.save()
            item = set_gitpod_user_expiration(item.id)
            serializer = GitpodUserSmallSerializer(item, many=False)
            return Response(serializer.data, status=status.HTTP_200_OK)

        serializer = GetGitpodUserSerializer(item, data=request.data)
        if serializer.is_valid():
            _item = serializer.save()
            return Response(GitpodUserSmallSerializer(_item, many=False).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProfileView(APIView, GenerateLookupsMixin):

    @capable_of("crud_event")
    def get(self, request, academy_id=None, user_id=None):

        item = Profile.objects.filter(user__id=user_id).first()
        if not item:
            raise ValidationException("Profile not found", code=404, slug="profile-not-found")

        serializer = GetProfileSerializer(item, many=False)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @capable_of("crud_event")
    def put(self, request, academy_id=None, user_id=None):

        item = Profile.objects.filter(user__id=user_id).first()
        if not item:
            raise ValidationException("Profile not found", code=404, slug="profile-not-found")

        serializer = ProfileSerializer(item, data=request.data)
        if serializer.is_valid():
            item = serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProfileMeView(APIView, GenerateLookupsMixin):

    @has_permission("get_my_profile")
    def get(self, request):
        item = Profile.objects.filter(user=request.user).first()
        if not item:
            raise ValidationException("Profile not found", code=404, slug="profile-not-found")

        serializer = GetProfileSerializer(item, many=False)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @has_permission("create_my_profile")
    def post(self, request):
        if Profile.objects.filter(user__id=request.user.id).exists():
            raise ValidationException("Profile already exists", code=400, slug="profile-already-exist")

        data = {}
        for key in request.data:
            data[key] = request.data[key]

        data["user"] = request.user.id

        serializer = ProfileSerializer(data=data)
        if serializer.is_valid():
            instance = serializer.save()
            serializer = GetProfileSerializer(instance, many=False)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @has_permission("update_my_profile")
    def put(self, request):
        item = Profile.objects.filter(user__id=request.user.id).first()
        if not item:
            raise ValidationException("Profile not found", code=404, slug="profile-not-found")

        data = {}
        for key in request.data:
            data[key] = request.data[key]

        data["user"] = request.user.id

        serializer = ProfileSerializer(item, data=data)
        if serializer.is_valid():
            instance = serializer.save()
            serializer = GetProfileSerializer(instance, many=False)
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProfileMePictureView(APIView):
    """
    put:
        Upload a file to Google Cloud.
    """

    parser_classes = [MultiPartParser, FileUploadParser]

    @has_permission("update_my_profile")
    def put(self, request):
        from ..services.google_cloud import Storage

        lang = get_user_language(request)

        profile = Profile.objects.filter(user=request.user).first()
        if not profile:
            profile = Profile(user=request.user)
            profile.save()

        files = request.data.getlist("file")
        file = request.data.get("file")

        if not file:
            raise ValidationException("Missing file in request", slug="missing-file")

        if not len(files):
            raise ValidationException("empty files in request")

        if len(files) > 1:
            raise ValidationException("Just can upload one file at a time")

        # files validation below
        if file.content_type not in PROFILE_MIME_ALLOWED:
            raise ValidationException(
                f'You can upload only files on the following formats: {",".join(PROFILE_MIME_ALLOWED)}',
                slug="bad-file-format",
            )

        file_bytes = file.read()
        hash = hashlib.sha256(file_bytes).hexdigest()

        try:
            storage = Storage()
            cloud_file = storage.file(get_profile_bucket(), hash)
            cloud_file_thumbnail = storage.file(get_profile_bucket(), f"{hash}-100x100")

            if thumb_exists := cloud_file_thumbnail.exists():
                cloud_file_thumbnail_url = cloud_file_thumbnail.url()

        except CircuitBreakerError:
            raise ValidationException(
                translation(
                    lang,
                    en="The circuit breaker is open due to an error, please try again later",
                    es="El circuit breaker está abierto debido a un error, por favor intente más tarde",
                    slug="circuit-breaker-open",
                ),
                slug="circuit-breaker-open",
                data={"service": "Google Cloud Storage"},
                silent=True,
                code=503,
            )

        if not thumb_exists:
            cloud_file.upload(file, content_type=file.content_type)
            func = FunctionV2(get_shape_of_image_url())

            res = func.call({"filename": hash, "bucket": get_profile_bucket()}, timeout=28)
            json = res.json()

            if json["shape"] != "Square":
                cloud_file.delete()
                raise ValidationException("just can upload square images", slug="not-square-image")

            func = FunctionV1(region="us-central1", project_id=get_google_project_id(), name="resize-image")

            res = func.call(
                {
                    "width": 100,
                    "filename": hash,
                    "bucket": get_profile_bucket(),
                },
                timeout=28,
            )

            try:
                cloud_file_thumbnail = storage.file(get_profile_bucket(), f"{hash}-100x100")
                cloud_file_thumbnail_url = cloud_file_thumbnail.url()

                cloud_file.delete()

            except CircuitBreakerError:
                raise ValidationException(
                    translation(
                        lang,
                        en="The circuit breaker is open due to an error, please try again later",
                        es="El circuit breaker está abierto debido a un error, por favor intente más tarde",
                        slug="circuit-breaker-open",
                    ),
                    slug="circuit-breaker-open",
                    data={"service": "Google Cloud Storage"},
                    silent=True,
                    code=503,
                )

        previous_avatar_url = profile.avatar_url or ""
        profile.avatar_url = cloud_file_thumbnail_url
        profile.save()

        if previous_avatar_url != profile.avatar_url:
            result = re.search(r"/(.{64})-100x100$", previous_avatar_url)

            if result:
                previous_hash = result[1]

                # remove the file when the last user remove their copy of the same image
                if not Profile.objects.filter(avatar_url__contains=previous_hash).exists():
                    try:
                        cloud_file = storage.file(get_profile_bucket(), f"{hash}-100x100")
                        cloud_file.delete()

                    except CircuitBreakerError:
                        raise ValidationException(
                            translation(
                                lang,
                                en="The circuit breaker is open due to an error, please try again later",
                                es="El circuit breaker está abierto debido a un error, por favor intente más tarde",
                                slug="circuit-breaker-open",
                            ),
                            slug="circuit-breaker-open",
                            data={"service": "Google Cloud Storage"},
                            silent=True,
                            code=503,
                        )

        serializer = GetProfileSerializer(profile, many=False)
        return Response(serializer.data, status=status.HTTP_200_OK)


class GithubMeView(APIView):

    def delete(self, request):
        instance = CredentialsGithub.objects.filter(user=request.user).first()
        if not instance:
            raise ValidationException(
                "This user not have Github account associated with with account", code=404, slug="not-found"
            )

        instance.delete()

        return Response(None, status=status.HTTP_204_NO_CONTENT)


# app/user/:id
class AppUserView(APIView):
    permission_classes = [AllowAny]
    extensions = APIViewExtensions(paginate=True)

    @scope(["read:user"])
    def get(self, request: LinkedHttpRequest, app: LinkedApp, token: LinkedToken, user_id=None):
        handler = self.extensions(request)
        lang = get_user_language(request)

        extra = {}
        if app.require_an_agreement:
            extra["appuseragreement__app__id"] = app.id

        if token.sub:
            user = request.get_user()
            extra["id"] = user.id

        if user_id:
            if "id" in extra and extra["id"] != user_id:
                raise ValidationException(
                    translation(
                        lang,
                        en="This user does not have access to this resource",
                        es="Este usuario no tiene acceso a este recurso",
                    ),
                    code=403,
                    slug="user-with-no-access",
                    silent=True,
                )

            if "id" not in extra:
                extra["id"] = user_id

            user = User.objects.filter(**extra).first()
            if not user:
                raise ValidationException(
                    translation(lang, en="User not found", es="Usuario no encontrado"),
                    code=404,
                    slug="user-not-found",
                    silent=True,
                )

            serializer = AppUserSerializer(user, many=False)
            return Response(serializer.data)

        if not token.sub and (id := request.GET.get("id")):
            extra["id"] = id

        for key in ["email", "username"]:
            if key in request.GET:
                extra[key] = request.GET.get(key)

        # test this path
        items = User.objects.filter(**extra)
        items = handler.queryset(items)
        serializer = AppUserSerializer(items, many=True)

        return handler.response(serializer.data)


class AppUserAgreementView(APIView):
    extensions = APIViewExtensions(paginate=True)

    def get(self, request):
        handler = self.extensions(request)

        items = AppUserAgreement.objects.filter(user=request.user, app__require_an_agreement=True)
        items = handler.queryset(items)
        serializer = SmallAppUserAgreementSerializer(items, many=True)

        return handler.response(serializer.data)


# app/user/:id
class AppSync(APIView):

    @sync_to_async
    def aget_user(self):
        return self.request.user

    @sync_to_async
    def aget_github_credentials(self):
        return CredentialsGithub.objects.filter(user=self.request.user).first()

    @sync_to_async
    def aget_profile(self):
        return Profile.objects.filter(user=self.request.user).first()

    async def post(self, request, app_slug: str):
        lang = await aget_user_language(request)
        user = await self.aget_user()

        # app = await aget_app(app_slug)
        async with Service(app_slug, user.id, proxy=True) as s:
            if s.app.require_an_agreement:
                raise ValidationException(
                    translation(
                        lang,
                        en="Can't sync with an external app",
                        es="No se puede sincronizar con una aplicación externa",
                        slug="external-app",
                    ),
                    slug="external-app",
                    silent=True,
                )

            data = {
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "profile": None,
                "credentialsgithub": None,
            }

            if profile := await self.aget_profile():
                data["profile"] = {
                    "avatar_url": profile.avatar_url,
                    "bio": profile.bio,
                    "phone": profile.phone,
                    "show_tutorial": profile.show_tutorial,
                    "twitter_username": profile.twitter_username,
                    "github_username": profile.github_username,
                    "portfolio_url": profile.portfolio_url,
                    "linkedin_url": profile.linkedin_url,
                    "blog": profile.blog,
                }

            if github_credentials := await self.aget_github_credentials():
                data["credentialsgithub"] = {
                    "github_id": github_credentials.github_id,
                    "token": github_credentials.token,
                    "email": github_credentials.email,
                    "avatar_url": github_credentials.avatar_url,
                    "name": github_credentials.name,
                    "username": github_credentials.username,
                    "blog": github_credentials.blog,
                    "bio": github_credentials.bio,
                    "company": github_credentials.company,
                    "twitter_username": github_credentials.twitter_username,
                }

            return await s.post("/v1/auth/app/user", data)
