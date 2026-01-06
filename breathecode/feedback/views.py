from datetime import datetime

from capyc.rest_framework.exceptions import ValidationException
from capyc.core.i18n import translation
from django.contrib.auth.models import User
from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
from PIL import Image
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
import logging

import breathecode.activity.tasks as tasks_activity
from breathecode.admissions.models import Academy, CohortUser
from breathecode.utils import GenerateLookupsMixin, HeaderLimitOffsetPagination, capable_of
from breathecode.utils.api_view_extensions.api_view_extensions import APIViewExtensions
from breathecode.utils.find_by_full_name import query_like_by_full_name

from .caches import AnswerCache
from .models import (
    AcademyFeedbackSettings,
    Answer,
    FeedbackTag,
    Review,
    ReviewPlatform,
    Survey,
    SurveyConfiguration,
    SurveyQuestionTemplate,
    SurveyResponse,
    SurveyStudy,
    SurveyTemplate,
)
from .serializers import (
    AcademyFeedbackSettingsPUTSerializer,
    AcademyFeedbackSettingsSerializer,
    AnswerPUTSerializer,
    AnswerSerializer,
    BigAnswerSerializer,
    FeedbackTagPOSTSerializer,
    FeedbackTagPUTSerializer,
    FeedbackTagSerializer,
    GetSurveySerializer,
    ReviewPlatformSerializer,
    ReviewPUTSerializer,
    ReviewSmallSerializer,
    SurveyAnswerSerializer,
    SurveyConfigurationSerializer,
    SurveyQuestionTemplateSerializer,
    SurveyPUTSerializer,
    SurveyResponseSerializer,
    SurveyStudySerializer,
    SurveySerializer,
    SurveySmallSerializer,
    SurveyTemplateSerializer,
)
from .tasks import generate_user_cohort_survey_answers


@api_view(["GET"])
@permission_classes([AllowAny])
def track_survey_open(request, answer_id=None):

    item = None
    if answer_id is not None:
        item = Answer.objects.filter(id=answer_id, status="SENT").first()

    if item is not None:
        item.status = "OPENED"
        item.opened_at = timezone.now()
        item.save()

    image = Image.new("RGBA", (1, 1), (0, 0, 0, 0))  # Creates fully transparent pixel ✅
    response = HttpResponse(content_type="image/png")
    image.save(response, "PNG")
    return response


@api_view(["GET"])
def track_survey_response_email_open(request, token=None):
    """
    Track survey email opens using a 1x1 transparent pixel.
    The token identifies the SurveyResponse; it sets email_opened_at only once.
    """
    if token is None:
        raise ValidationException("Missing token", code=400, slug="missing-token")

    survey_response = SurveyResponse.objects.filter(token=token).first()
    if survey_response and survey_response.email_opened_at is None:
        survey_response.email_opened_at = timezone.now()
        survey_response.save(update_fields=["email_opened_at"])
        try:
            from breathecode.feedback.actions import update_survey_stats

            update_survey_stats(survey_response)
        except Exception:
            logging.getLogger(__name__).exception("[survey-response] unable to update stats after email open")

    image = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    response = HttpResponse(content_type="image/png")
    image.save(response, "PNG")
    return response


@api_view(["GET"])
def get_survey_questions(request, survey_id=None):

    survey = Survey.objects.filter(id=survey_id).first()
    if survey is None:
        raise ValidationException("Survey not found", 404)

    utc_now = timezone.now()
    if utc_now > survey.sent_at + survey.duration:
        raise ValidationException("This survey has already expired", 400)

    cu = CohortUser.objects.filter(cohort=survey.cohort, role="STUDENT", user=request.user).first()
    if cu is None:
        raise ValidationException("This student does not belong to this cohort", 400)

    cohort_teacher = CohortUser.objects.filter(cohort=survey.cohort, role="TEACHER")
    if cohort_teacher.count() == 0:
        raise ValidationException("This cohort must have a teacher assigned to be able to survey it", 400)

    template_slug = survey.template_slug
    if template_slug is None:
        # If the survey does not have a template slug, we need to get the default template slug
        # from the AcademyFeedbackSettings model
        settings = AcademyFeedbackSettings.objects.filter(academy=survey.cohort.academy).first()
        template_slug = settings.cohort_survey_template.slug if settings and settings.cohort_survey_template else None
        survey.template_slug = template_slug
        survey.save()

    answers = generate_user_cohort_survey_answers(request.user, survey, status="OPENED", template_slug=template_slug)
    serializer = AnswerSerializer(answers, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET"])
def get_survey(request, survey_id=None):

    survey = Survey.objects.filter(id=survey_id).first()
    if survey is None:
        raise ValidationException("Survey not found", 404)

    utc_now = timezone.now()
    if utc_now > survey.sent_at + survey.duration:
        raise ValidationException("This survey has already expired", 400)

    serializer = SurveySerializer(survey)
    return Response(serializer.data, status=status.HTTP_200_OK)


# Create your views here.
class GetAnswerView(APIView):
    """
    List all snippets, or create a new snippet.
    """

    extensions = APIViewExtensions(cache=AnswerCache, sort="-created_at", paginate=True)

    @capable_of("read_nps_answers")
    def get(self, request, format=None, academy_id=None):
        handler = self.extensions(request)

        cache = handler.cache.get()
        if cache is not None:
            return cache

        items = Answer.objects.filter(academy__id=academy_id)

        lookup = {}

        users = request.GET.get("user", None)
        if users is not None and users != "":
            items = items.filter(user__id__in=users.split(","))

        cohorts = request.GET.get("cohort", None)
        if cohorts is not None and cohorts != "":
            items = items.filter(cohort__slug__in=cohorts.split(","))

        mentors = request.GET.get("mentor", None)
        if mentors is not None and mentors != "":
            items = items.filter(mentor__id__in=mentors.split(","))

        events = request.GET.get("event", None)
        if events is not None and events != "":
            items = items.filter(event__id__in=events.split(","))

        score = request.GET.get("score", None)
        if score is not None and score != "":
            lookup["score"] = score

        _status = request.GET.get("status", None)
        if _status is not None and _status != "":
            items = items.filter(status__in=_status.split(","))

        surveys = request.GET.get("survey", None)
        if surveys is not None and surveys != "":
            items = items.filter(survey__id__in=surveys.split(","))

        items = items.filter(**lookup)

        like = request.GET.get("like", None)
        if like is not None:
            items = query_like_by_full_name(like=like, items=items, prefix="user__")

        items = handler.queryset(items)
        serializer = AnswerSerializer(items, many=True)

        return handler.response(serializer.data)


class AnswerMeView(APIView):
    """
    Student answers a survey (normally several answers are required for each survey)
    """

    def put(self, request, answer_id=None):
        if answer_id is None:
            raise ValidationException("Missing answer_id", slug="missing-answer-id")

        answer = Answer.objects.filter(user=request.user, id=answer_id).first()
        if answer is None:
            raise ValidationException(
                "This survey does not exist for this user", code=404, slug="answer-of-other-user-or-not-exists"
            )

        serializer = AnswerPUTSerializer(answer, data=request.data, context={"request": request, "answer": answer_id})
        if serializer.is_valid():
            tasks_activity.add_activity.delay(
                request.user.id, "nps_answered", related_type="feedback.Answer", related_id=answer_id
            )
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, answer_id=None):
        if answer_id is None:
            raise ValidationException("Missing answer_id", slug="missing-answer-id")

        answer = Answer.objects.filter(user=request.user, id=answer_id).first()
        if answer is None:
            raise ValidationException(
                "This survey does not exist for this user", code=404, slug="answer-of-other-user-or-not-exists"
            )

        serializer = BigAnswerSerializer(answer)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AcademyAnswerView(APIView):

    @capable_of("read_nps_answers")
    def get(self, request, academy_id=None, answer_id=None):
        if answer_id is None:
            raise ValidationException("Missing answer_id", code=404)

        answer = Answer.objects.filter(academy__id=academy_id, id=answer_id).first()
        if answer is None:
            raise ValidationException("This survey does not exist for this academy")

        serializer = BigAnswerSerializer(answer)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AcademySurveyView(APIView, HeaderLimitOffsetPagination, GenerateLookupsMixin):
    """
    List all snippets, or create a new snippet.
    """

    @capable_of("crud_survey")
    def post(self, request, academy_id=None):

        serializer = SurveySerializer(data=request.data, context={"request": request, "academy_id": academy_id})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    """
    List all snippets, or create a new snippet.
    """

    @capable_of("crud_survey")
    def put(self, request, survey_id=None, academy_id=None):
        if survey_id is None:
            raise ValidationException("Missing survey_id")

        survey = Survey.objects.filter(id=survey_id).first()
        if survey is None:
            raise NotFound("This survey does not exist")

        serializer = SurveyPUTSerializer(
            survey, data=request.data, context={"request": request, "survey": survey_id, "academy_id": academy_id}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of("read_survey")
    def get(self, request, survey_id=None, academy_id=None):
        if survey_id is not None:
            survey = Survey.objects.filter(id=survey_id).first()
            if survey is None:
                raise NotFound("This survey does not exist")

            serializer = GetSurveySerializer(survey)
            return Response(serializer.data, status=status.HTTP_200_OK)

        items = Survey.objects.filter(cohort__academy__id=academy_id)
        lookup = {}

        if "status" in self.request.GET:
            param = self.request.GET.get("status")
            lookup["status"] = param

        if "cohort" in self.request.GET:
            param = self.request.GET.get("cohort")
            lookup["cohort__slug"] = param

        if "lang" in self.request.GET:
            param = self.request.GET.get("lang")
            lookup["lang"] = param

        if "template_slug" in self.request.GET:
            param = self.request.GET.get("template_slug")
            lookup["template_slug"] = param

        if "title" in self.request.GET:
            title = self.request.GET.get("title")
            items = items.filter(title__icontains=title)

        if "total_score" in self.request.GET:
            total_score = self.request.GET.get("total_score")
            lookup_map = {
                "gte": "scores__total__gte",
                "lte": "scores__total__lte",
                "gt": "scores__total__gt",
                "lt": "scores__total__lt",
            }

            try:
                # Check for prefix (e.g., gte:8)
                if ":" in total_score:
                    prefix, value = total_score.split(":", 1)
                    if prefix in lookup_map:
                        score_value = int(value)
                        items = items.filter(**{lookup_map[prefix]: score_value})
                    else:
                        raise ValidationException(f"Invalid total_score format {total_score}", slug="score-format")
                else:
                    # Exact match (e.g., 8)
                    score_value = int(total_score)
                    items = items.filter(scores__total__gte=score_value, scores__total__lt=score_value + 1)
            except ValueError:
                raise ValidationException(f"Invalid total_score format {total_score}", slug="score-format")

        sort = self.request.GET.get("sort")
        if sort is None:
            sort = "-created_at"
        items = items.filter(**lookup).order_by(sort)

        page = self.paginate_queryset(items, request)
        serializer = SurveySmallSerializer(page, many=True)

        if self.is_paginate(request):
            return self.get_paginated_response(serializer.data)
        else:
            return Response(serializer.data, status=status.HTTP_200_OK)

    @capable_of("crud_survey")
    def delete(self, request, academy_id=None, survey_id=None):

        lookups = self.generate_lookups(request, many_fields=["id"])

        if lookups and survey_id:
            raise ValidationException(
                "survey_id was provided in url " "in bulk mode request, use querystring style instead",
                code=400,
                slug="survey-id-and-lookups-together",
            )

        if not lookups and not survey_id:
            raise ValidationException(
                "survey_id was not provided in url", code=400, slug="without-survey-id-and-lookups"
            )

        if lookups:
            items = Survey.objects.filter(**lookups, cohort__academy__id=academy_id).exclude(status="SENT")

            ids = [item.id for item in items]

            if answers := Answer.objects.filter(survey__id__in=ids, status="ANSWERED"):

                slugs = set([answer.survey.cohort.slug for answer in answers])

                raise ValidationException(
                    f'Survey cannot be deleted because it has been answered for cohorts {", ".join(slugs)}',
                    code=400,
                    slug="survey-cannot-be-deleted",
                )

            for item in items:
                item.delete()

            return Response(None, status=status.HTTP_204_NO_CONTENT)

        sur = Survey.objects.filter(id=survey_id, cohort__academy__id=academy_id).exclude(status="SENT").first()
        if sur is None:
            raise ValidationException("Survey not found", 404, slug="survey-not-found")

        if Answer.objects.filter(survey__id=survey_id, status="ANSWERED"):
            raise ValidationException("Survey cannot be deleted", code=400, slug="survey-cannot-be-deleted")

        sur.delete()
        return Response(None, status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
@permission_classes([AllowAny])
def get_review_platform(request, platform_slug=None):

    items = ReviewPlatform.objects.all()
    if platform_slug is not None:
        items = items.filter(slug=platform_slug).first()
        if items is not None:
            serializer = ReviewPlatformSerializer(items, many=False)
            return Response(serializer.data)
        else:
            raise ValidationException("Review platform not found", slug="reivew_platform_not_found", code=404)
    else:
        serializer = ReviewPlatformSerializer(items, many=True)
        return Response(serializer.data)


@api_view(["GET"])
@permission_classes([AllowAny])
def get_reviews(request):
    """
    List all snippets, or create a new snippet.
    """
    items = Review.objects.filter(
        is_public=True,
        status="DONE",
        comments__isnull=False,
        total_rating__isnull=False,
        total_rating__gt=0,
        total_rating__lte=10,
    ).exclude(comments__exact="")

    lookup = {}

    if "academy" in request.GET:
        param = request.GET.get("academy")
        lookup["cohort__academy__id"] = param

    if "lang" in request.GET:
        param = request.GET.get("lang")
        lookup["lang"] = param

    items = items.filter(**lookup).order_by("-created_at")

    serializer = ReviewSmallSerializer(items, many=True)
    return Response(serializer.data)


class ReviewView(APIView, HeaderLimitOffsetPagination, GenerateLookupsMixin):
    """
    List all snippets, or create a new snippet.
    """

    @capable_of("read_review")
    def get(self, request, format=None, academy_id=None):

        academy = Academy.objects.get(id=academy_id)
        items = Review.objects.filter(cohort__academy__id=academy.id)
        lookup = {}

        start = request.GET.get("start", None)
        if start is not None:
            start_date = datetime.strptime(start, "%Y-%m-%d").date()
            lookup["created_at__gte"] = start_date

        end = request.GET.get("end", None)
        if end is not None:
            end_date = datetime.strptime(end, "%Y-%m-%d").date()
            lookup["created_at__lte"] = end_date

        if "status" in self.request.GET:
            param = self.request.GET.get("status")
            lookup["status"] = param

        if "platform" in self.request.GET:
            param = self.request.GET.get("platform")
            items = items.filter(platform__name__icontains=param)

        if "cohort" in self.request.GET:
            param = self.request.GET.get("cohort")
            lookup["cohort__id"] = param

        if "author" in self.request.GET:
            param = self.request.GET.get("author")
            lookup["author__id"] = param

        sort_by = "-created_at"
        if "sort" in self.request.GET and self.request.GET["sort"] != "":
            sort_by = self.request.GET.get("sort")

        items = items.filter(**lookup).order_by(sort_by)

        like = request.GET.get("like", None)
        if like is not None:
            items = query_like_by_full_name(like=like, items=items, prefix="author__")

        page = self.paginate_queryset(items, request)
        serializer = ReviewSmallSerializer(page, many=True)

        if self.is_paginate(request):
            return self.get_paginated_response(serializer.data)
        else:
            return Response(serializer.data, status=200)

    @capable_of("crud_review")
    def put(self, request, review_id, academy_id=None):

        review = Review.objects.filter(id=review_id, cohort__academy__id=academy_id).first()
        if review is None:
            raise NotFound("This review does not exist on this academy")

        serializer = ReviewPUTSerializer(
            review, data=request.data, context={"request": request, "review": review_id, "academy_id": academy_id}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of("crud_review")
    def delete(self, request, academy_id=None):
        # TODO: here i don't add one single delete, because i don't know if it is required
        lookups = self.generate_lookups(request, many_fields=["id"])
        # automation_objects

        if not lookups:
            raise ValidationException("Missing parameters in the querystring", code=400)

        items = Review.objects.filter(**lookups, academy__id=academy_id)

        for item in items:
            item.status = "IGNORE"
            item.save()

        return Response(None, status=status.HTTP_204_NO_CONTENT)


class AcademyFeedbackSettingsView(APIView):
    @capable_of("get_academy_feedback_settings")
    def get(self, request, academy_id):

        try:
            settings = AcademyFeedbackSettings.objects.get(academy__id=academy_id)
        except AcademyFeedbackSettings.DoesNotExist:
            raise ValidationException("Academy feedback settings not found", code=400)

        serializer = AcademyFeedbackSettingsSerializer(settings)
        return Response(serializer.data)

    @capable_of("crud_academy_feedback_settings")
    def put(self, request, academy_id):
        academy = Academy.objects.get(id=academy_id)
        # Look for a shared English template to use as default
        default_template = SurveyTemplate.objects.filter(
            is_shared=True, lang="en", original__isnull=True  # Only get original templates
        ).first()

        defaults = {}

        # Add template to defaults if found
        if "cohort_survey_template" not in request.data:
            defaults["cohort_survey_template"] = default_template
        if "liveclass_survey_template" not in request.data:
            defaults["liveclass_survey_template"] = default_template
        if "event_survey_template" not in request.data:
            defaults["event_survey_template"] = default_template
        if "mentorship_session_survey_template" not in request.data:
            defaults["mentorship_session_survey_template"] = default_template

        settings, created = AcademyFeedbackSettings.objects.get_or_create(academy=academy, defaults=defaults)

        serializer = AcademyFeedbackSettingsPUTSerializer(
            settings, data=request.data, context={"request": request, "academy_id": academy_id}
        )

        if serializer.is_valid():
            serializer.save()
            return Response(AcademyFeedbackSettingsSerializer(settings).data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AcademySurveyTemplateView(APIView):
    @capable_of("read_survey_template")
    def get(self, request, academy_id=None):
        templates = SurveyTemplate.objects.filter(Q(academy__id=academy_id) | Q(is_shared=True))

        # Check if 'is_shared' is present and true in the querystring
        is_shared = request.GET.get("is_shared", "false").lower() == "false"
        if is_shared:
            templates = templates.filter(is_shared=False)

        if "lang" in self.request.GET:
            param = self.request.GET.get("lang")
            templates = templates.filter(lang=param)

        serializer = SurveyTemplateSerializer(templates, many=True)
        return Response(serializer.data)


class AcademyFeedbackTagView(APIView, GenerateLookupsMixin):
    """
    CRUD endpoints for managing FeedbackTag
    """

    @capable_of("read_nps_answers")
    def get(self, request, academy_id=None, tag_id=None):
        """
        Get FeedbackTags. Returns academy-owned tags and public shared tags.
        Sorted by priority (ascending) by default.
        """
        if tag_id is not None:
            # Get single tag
            tag = FeedbackTag.objects.filter(
                Q(id=tag_id) & (Q(academy__id=academy_id) | (Q(academy__isnull=True) & Q(is_private=False)))
            ).first()

            if tag is None:
                raise ValidationException("Tag not found or not accessible", code=404, slug="tag-not-found")

            serializer = FeedbackTagSerializer(tag)
            return Response(serializer.data, status=status.HTTP_200_OK)

        # List tags - include academy's tags and public shared tags
        tags = FeedbackTag.objects.filter(Q(academy__id=academy_id) | (Q(academy__isnull=True) & Q(is_private=False)))

        # Filter by academy if specified in query params
        academy_filter = request.GET.get("academy", None)
        if academy_filter is not None:
            if academy_filter.lower() == "mine":
                # Only tags owned by this academy
                tags = tags.filter(academy__id=academy_id)
            elif academy_filter.lower() == "shared":
                # Only shared public tags
                tags = tags.filter(academy__isnull=True, is_private=False)

        # Default sort by priority, then title
        sort = request.GET.get("sort", "priority")
        tags = tags.order_by(sort)

        serializer = FeedbackTagSerializer(tags, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @capable_of("crud_survey")
    def post(self, request, academy_id=None):
        """
        Create a new FeedbackTag
        """
        academy = Academy.objects.get(id=academy_id)

        # If academy is not specified in payload, use the current academy
        if "academy" not in request.data or request.data["academy"] is None:
            data = request.data.copy()
            data["academy"] = academy.id
        else:
            data = request.data

        serializer = FeedbackTagPOSTSerializer(data=data, context={"request": request, "academy_id": academy_id})

        if serializer.is_valid():
            serializer.save()
            return Response(FeedbackTagSerializer(serializer.instance).data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of("crud_survey")
    def put(self, request, academy_id=None, tag_id=None):
        """
        Update an existing FeedbackTag
        """
        if tag_id is None:
            raise ValidationException("Missing tag_id", code=400, slug="missing-tag-id")

        # Can only update tags owned by this academy
        tag = FeedbackTag.objects.filter(id=tag_id, academy__id=academy_id).first()

        if tag is None:
            raise ValidationException(
                "Tag not found or you don't have permission to edit it", code=404, slug="tag-not-found-or-forbidden"
            )

        serializer = FeedbackTagPUTSerializer(
            tag, data=request.data, context={"request": request, "academy_id": academy_id}
        )

        if serializer.is_valid():
            serializer.save()
            return Response(FeedbackTagSerializer(serializer.instance).data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of("crud_survey")
    def delete(self, request, academy_id=None, tag_id=None):
        """
        Delete FeedbackTag(s). Supports bulk delete via query string.
        """
        lookups = self.generate_lookups(request, many_fields=["id"])

        if lookups and tag_id:
            raise ValidationException(
                "tag_id was provided in url in bulk mode request, use querystring style instead",
                code=400,
                slug="tag-id-and-lookups-together",
            )

        if not lookups and not tag_id:
            raise ValidationException("tag_id was not provided in url", code=400, slug="without-tag-id-and-lookups")

        if lookups:
            # Bulk delete - only delete tags owned by this academy
            items = FeedbackTag.objects.filter(**lookups, academy__id=academy_id)

            for item in items:
                item.delete()

            return Response(None, status=status.HTTP_204_NO_CONTENT)

        # Single delete
        tag = FeedbackTag.objects.filter(id=tag_id, academy__id=academy_id).first()

        if tag is None:
            raise ValidationException(
                "Tag not found or you don't have permission to delete it",
                code=404,
                slug="tag-not-found-or-forbidden",
            )

        tag.delete()
        return Response(None, status=status.HTTP_204_NO_CONTENT)


class SurveyConfigurationView(APIView, HeaderLimitOffsetPagination, GenerateLookupsMixin):
    """View for managing survey configurations."""

    @capable_of("read_survey")
    def get(self, request, academy_id=None, configuration_id=None):
        """List or get survey configurations."""
        if configuration_id:
            config = SurveyConfiguration.objects.filter(id=configuration_id, academy__id=academy_id).first()
            if not config:
                raise NotFound("Survey configuration not found")

            serializer = SurveyConfigurationSerializer(config)
            return Response(serializer.data, status=status.HTTP_200_OK)

        # List all configurations for this academy
        items = SurveyConfiguration.objects.filter(academy__id=academy_id)
        lookups = self.generate_lookups(request, many_fields=["id", "trigger_type"])

        if lookups:
            items = items.filter(**lookups)

        items = items.order_by("-created_at")

        page = self.paginate_queryset(items, request)
        if page is not None:
            serializer = SurveyConfigurationSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = SurveyConfigurationSerializer(items, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @capable_of("crud_survey")
    def post(self, request, academy_id=None):
        """Create a new survey configuration."""
        serializer = SurveyConfigurationSerializer(
            data=request.data, context={"request": request, "academy_id": academy_id}
        )

        if serializer.is_valid():
            # Set academy and created_by
            academy = Academy.objects.filter(id=academy_id).first()
            if not academy:
                raise ValidationException("Academy not found", code=404, slug="academy-not-found")

            survey_config = serializer.save(academy=academy, created_by=request.user)
            return Response(SurveyConfigurationSerializer(survey_config).data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of("crud_survey")
    def put(self, request, academy_id=None, configuration_id=None):
        """Update a survey configuration."""
        if not configuration_id:
            raise ValidationException("Missing configuration_id", code=400, slug="missing-configuration-id")

        config = SurveyConfiguration.objects.filter(id=configuration_id, academy__id=academy_id).first()
        if not config:
            raise NotFound("Survey configuration not found")

        serializer = SurveyConfigurationSerializer(
            config, data=request.data, context={"request": request, "academy_id": academy_id}, partial=True
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SurveyQuestionTemplateView(APIView, HeaderLimitOffsetPagination, GenerateLookupsMixin):
    """
    CRUD for SurveyQuestionTemplate (new survey system templates).

    Note: templates are global (not academy-owned), but access is still restricted by academy capabilities.
    """

    @capable_of("crud_survey")
    def post(self, request, academy_id=None):
        serializer = SurveyQuestionTemplateSerializer(data=request.data)
        if serializer.is_valid():
            item = serializer.save()
            return Response(SurveyQuestionTemplateSerializer(item).data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of("read_survey")
    def get(self, request, academy_id=None, template_id=None):
        if template_id is not None:
            item = SurveyQuestionTemplate.objects.filter(id=template_id).first()
            if not item:
                raise NotFound("Survey template not found")

            serializer = SurveyQuestionTemplateSerializer(item)
            return Response(serializer.data, status=status.HTTP_200_OK)

        items = SurveyQuestionTemplate.objects.all().order_by("-created_at")
        lookups = self.generate_lookups(request, many_fields=["id", "slug"])
        if lookups:
            items = items.filter(**lookups)

        page = self.paginate_queryset(items, request)
        if page is not None:
            serializer = SurveyQuestionTemplateSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = SurveyQuestionTemplateSerializer(items, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @capable_of("crud_survey")
    def put(self, request, academy_id=None, template_id=None):
        if template_id is None:
            raise ValidationException("Missing template_id", code=400, slug="missing-template-id")

        item = SurveyQuestionTemplate.objects.filter(id=template_id).first()
        if not item:
            raise NotFound("Survey template not found")

        serializer = SurveyQuestionTemplateSerializer(item, data=request.data, partial=True)
        if serializer.is_valid():
            item = serializer.save()
            return Response(SurveyQuestionTemplateSerializer(item).data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of("crud_survey")
    def delete(self, request, academy_id=None, template_id=None):
        if template_id is None:
            raise ValidationException("Missing template_id", code=400, slug="missing-template-id")

        item = SurveyQuestionTemplate.objects.filter(id=template_id).first()
        if not item:
            raise NotFound("Survey template not found")

        item.delete()
        return Response(None, status=status.HTTP_204_NO_CONTENT)


class SurveyStudyView(APIView, HeaderLimitOffsetPagination, GenerateLookupsMixin):
    """CRUD for SurveyStudy (academy-scoped)."""

    @capable_of("crud_survey")
    def post(self, request, academy_id=None, **kwargs):
        academy = Academy.objects.filter(id=academy_id).first()
        if not academy:
            raise ValidationException("Academy not found", code=404, slug="academy-not-found")

        serializer = SurveyStudySerializer(data=request.data)
        if serializer.is_valid():
            item = serializer.save(academy=academy)
            return Response(SurveyStudySerializer(item).data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of("read_survey")
    def get(self, request, academy_id=None, study_id=None, **kwargs):
        if study_id is not None:
            item = SurveyStudy.objects.filter(id=study_id, academy__id=academy_id).first()
            if not item:
                raise NotFound("Survey study not found")

            serializer = SurveyStudySerializer(item)
            return Response(serializer.data, status=status.HTTP_200_OK)

        items = SurveyStudy.objects.filter(academy__id=academy_id).order_by("-created_at")
        lookups = self.generate_lookups(request, many_fields=["id", "slug"])
        if lookups:
            items = items.filter(**lookups)

        page = self.paginate_queryset(items, request)
        if page is not None:
            serializer = SurveyStudySerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = SurveyStudySerializer(items, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @capable_of("crud_survey")
    def put(self, request, academy_id=None, study_id=None, **kwargs):
        if study_id is None:
            raise ValidationException("Missing study_id", code=400, slug="missing-study-id")

        item = SurveyStudy.objects.filter(id=study_id, academy__id=academy_id).first()
        if not item:
            raise NotFound("Survey study not found")

        serializer = SurveyStudySerializer(item, data=request.data, partial=True)
        if serializer.is_valid():
            item = serializer.save()
            return Response(SurveyStudySerializer(item).data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of("crud_survey")
    def delete(self, request, academy_id=None, study_id=None, **kwargs):
        if study_id is None:
            raise ValidationException("Missing study_id", code=400, slug="missing-study-id")

        item = SurveyStudy.objects.filter(id=study_id, academy__id=academy_id).first()
        if not item:
            raise NotFound("Survey study not found")

        item.delete()
        return Response(None, status=status.HTTP_204_NO_CONTENT)


class SurveyStudySendEmailsView(APIView):
    """
    Staff endpoint to send a SurveyStudy survey to a list of users by email.

    It will:
    - create SurveyResponse objects for users that don't have one in this study (one per user per study)
    - distribute users across the study SurveyConfigurations using round-robin (equitable split)
    - enqueue `send_survey_response_email` Celery task for each created response
    - store optional `callback` in trigger_context and append it to the email LINK as `?callback=...`
    """

    @capable_of("crud_survey")
    def post(self, request, academy_id=None, study_id=None, **kwargs):
        if study_id is None:
            raise ValidationException(
                translation(en="Missing study_id", es="Falta study_id"),
                code=400,
                slug="missing-study-id",
            )

        study = SurveyStudy.objects.filter(id=study_id, academy__id=academy_id).first()
        if not study:
            raise ValidationException(
                translation(en="SurveyStudy not found", es="SurveyStudy no encontrado"),
                code=404,
                slug="survey-study-not-found",
            )

        user_ids = request.data.get("user_ids") or request.data.get("users") or []
        cohort_id = request.data.get("cohort_id", None)
        cohort_ids = request.data.get("cohort_ids", None)

        if cohort_id is not None and cohort_ids is not None:
            raise ValidationException(
                translation(
                    en="Use only one of cohort_id or cohort_ids",
                    es="Usa solo uno entre cohort_id o cohort_ids",
                ),
                code=400,
                slug="cohort-id-and-cohort-ids-together",
            )

        if cohort_id is not None:
            cohort_ids = [cohort_id]

        if cohort_ids is not None:
            if not isinstance(cohort_ids, list) or len(cohort_ids) == 0:
                raise ValidationException(
                    translation(
                        en="cohort_ids must be a non-empty list of integers",
                        es="cohort_ids debe ser una lista no vacía de enteros",
                    ),
                    code=400,
                    slug="invalid-cohort-ids",
                )

            cohort_user_ids = list(
                CohortUser.objects.filter(
                    cohort__id__in=cohort_ids,
                    role="STUDENT",
                    educational_status__in=["ACTIVE", "GRADUATED"],
                )
                .values_list("user_id", flat=True)
                .distinct()
            )

            # merge cohort users with provided user_ids
            if user_ids and not isinstance(user_ids, list):
                raise ValidationException(
                    translation(
                        en="user_ids must be a list when provided",
                        es="user_ids debe ser una lista cuando se provee",
                    ),
                    code=400,
                    slug="invalid-user-ids",
                )

            user_ids = list(dict.fromkeys([*cohort_user_ids, *(user_ids or [])]))

        if not isinstance(user_ids, list) or len(user_ids) == 0:
            raise ValidationException(
                translation(
                    en="Provide user_ids or cohort_id/cohort_ids",
                    es="Provee user_ids o cohort_id/cohort_ids",
                ),
                code=400,
                slug="missing-recipients",
            )

        callback = request.data.get("callback", None)
        if callback is not None and not isinstance(callback, str):
            raise ValidationException(
                translation(en="callback must be a string", es="callback debe ser un string"),
                code=400,
                slug="invalid-callback",
            )

        dry_run = bool(request.data.get("dry_run", False))

        utc_now = timezone.now()
        if study.starts_at and study.starts_at > utc_now:
            raise ValidationException(
                translation(en="SurveyStudy has not started yet", es="SurveyStudy no ha empezado todavía"),
                code=400,
                slug="study-not-started",
            )
        if study.ends_at and study.ends_at < utc_now:
            raise ValidationException(
                translation(en="SurveyStudy already ended", es="SurveyStudy ya terminó"),
                code=400,
                slug="study-ended",
            )

        configs = list(
            study.survey_configurations.filter(academy__id=academy_id, is_active=True).order_by("id")
        )
        if len(configs) == 0:
            raise ValidationException(
                translation(
                    en="SurveyStudy has no active survey configurations",
                    es="SurveyStudy no tiene configuraciones activas",
                ),
                code=400,
                slug="study-without-configs",
            )

        # fetch users in bulk
        existing_users = {u.id: u for u in User.objects.filter(id__in=user_ids)}

        from breathecode.feedback.actions import create_survey_response
        from breathecode.feedback.tasks import send_survey_response_email

        created = []
        skipped_existing = []
        skipped_missing_user = []
        scheduled = 0

        for i, raw_id in enumerate(user_ids):
            try:
                uid = int(raw_id)
            except Exception:
                skipped_missing_user.append({"user_id": raw_id, "reason": "invalid"})
                continue

            user = existing_users.get(uid)
            if not user:
                skipped_missing_user.append({"user_id": uid, "reason": "not_found"})
                continue

            existing = SurveyResponse.objects.filter(survey_study=study, user=user).first()
            if existing:
                skipped_existing.append(
                    {
                        "user_id": user.id,
                        "survey_response_id": existing.id,
                        "token": str(existing.token) if existing.token else None,
                    }
                )
                continue

            config = configs[i % len(configs)]
            context = {"source": "study_email"}
            if callback:
                context["callback"] = callback

            if dry_run:
                created.append(
                    {
                        "user_id": user.id,
                        "survey_config_id": config.id,
                        "survey_response_id": None,
                        "token": None,
                        "scheduled": False,
                    }
                )
                continue

            survey_response = create_survey_response(
                config,
                user,
                context,
                survey_study=study,
                send_pusher=False,
            )
            if not survey_response:
                created.append(
                    {
                        "user_id": user.id,
                        "survey_config_id": config.id,
                        "survey_response_id": None,
                        "token": None,
                        "scheduled": False,
                    }
                )
                continue

            send_survey_response_email.delay(survey_response.id)
            scheduled += 1

            created.append(
                {
                    "user_id": user.id,
                    "survey_config_id": config.id,
                    "survey_response_id": survey_response.id,
                    "token": str(survey_response.token) if survey_response.token else None,
                    "scheduled": True,
                }
            )

        return Response(
            {
                "study_id": study.id,
                "academy_id": int(academy_id) if academy_id is not None else None,
                "dry_run": dry_run,
                "configs_used": [c.id for c in configs],
                "created": created,
                "skipped_existing": skipped_existing,
                "skipped_missing_user": skipped_missing_user,
                "scheduled": scheduled,
            },
            status=status.HTTP_200_OK,
        )


class SurveyResponseView(APIView):
    """View for managing survey responses."""

    def get(self, request, response_id=None):
        """Get a survey response (user can only see their own)."""
        if not response_id:
            raise ValidationException("Missing response_id", code=400, slug="missing-response-id")

        survey_response = SurveyResponse.objects.filter(id=response_id, user=request.user).first()
        if not survey_response:
            raise NotFound("Survey response not found or you don't have permission to view it")

        serializer = SurveyResponseSerializer(survey_response)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, response_id=None):
        """Submit answers for a survey response."""
        from breathecode.feedback import actions

        if not response_id:
            raise ValidationException("Missing response_id", code=400, slug="missing-response-id")

        # Verify user owns this response
        survey_response = SurveyResponse.objects.filter(id=response_id, user=request.user).first()
        if not survey_response:
            raise NotFound("Survey response not found or you don't have permission to answer it")

        if survey_response.status == SurveyResponse.Status.ANSWERED:
            raise ValidationException("Survey already answered", code=400, slug="survey-already-answered")

        # Validate answers
        answer_serializer = SurveyAnswerSerializer(data={"answers": request.data.get("answers", {})})
        if not answer_serializer.is_valid():
            return Response(answer_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Save answers
        try:
            updated_response = actions.save_survey_answers(
                response_id, answer_serializer.validated_data["answers"]
            )
            serializer = SurveyResponseSerializer(updated_response)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ValidationException as e:
            return Response({"detail": str(e), "slug": e.slug}, status=status.HTTP_400_BAD_REQUEST)


class SurveyResponseByTokenView(APIView):
    """Get a SurveyResponse by token (requires login; user can only see their own)."""

    def get(self, request, token=None):
        if not token:
            raise ValidationException("Missing token", code=400, slug="missing-token")

        survey_response = SurveyResponse.objects.filter(token=token, user=request.user).first()
        if not survey_response:
            raise NotFound("Survey response not found or you don't have permission to view it")

        serializer = SurveyResponseSerializer(survey_response)
        return Response(serializer.data, status=status.HTTP_200_OK)


class SurveyResponseOpenedView(APIView):
    """Mark a SurveyResponse as opened (idempotent)."""

    def post(self, request, response_id=None):
        if not response_id:
            raise ValidationException("Missing response_id", code=400, slug="missing-response-id")

        survey_response = SurveyResponse.objects.filter(id=response_id, user=request.user).first()
        if not survey_response:
            raise NotFound("Survey response not found or you don't have permission to update it")

        if survey_response.opened_at is None:
            survey_response.opened_at = timezone.now()

        if survey_response.status == SurveyResponse.Status.PENDING:
            survey_response.status = SurveyResponse.Status.OPENED

        survey_response.save()
        try:
            from breathecode.feedback.actions import update_survey_stats

            update_survey_stats(survey_response)
        except Exception:
            logger = logging.getLogger(__name__)
            logger.exception("[survey-response] unable to update stats after opened")
        serializer = SurveyResponseSerializer(survey_response)
        return Response(serializer.data, status=status.HTTP_200_OK)


class SurveyResponsePartialView(APIView):
    """Save partial answers (draft) for a SurveyResponse (idempotent)."""

    def post(self, request, response_id=None):
        if not response_id:
            raise ValidationException("Missing response_id", code=400, slug="missing-response-id")

        survey_response = SurveyResponse.objects.filter(id=response_id, user=request.user).first()
        if not survey_response:
            raise NotFound("Survey response not found or you don't have permission to update it")

        if survey_response.status == SurveyResponse.Status.ANSWERED:
            raise ValidationException("Survey already answered", code=400, slug="survey-already-answered")

        answers = request.data.get("answers", {})
        if not isinstance(answers, dict):
            raise ValidationException("answers must be a dictionary", code=400, slug="invalid-answers-structure")

        if survey_response.opened_at is None:
            survey_response.opened_at = timezone.now()

        survey_response.answers = answers
        survey_response.status = SurveyResponse.Status.PARTIAL
        survey_response.save()
        try:
            from breathecode.feedback.actions import update_survey_stats

            update_survey_stats(survey_response)
        except Exception:
            logger = logging.getLogger(__name__)
            logger.exception("[survey-response] unable to update stats after partial")

        serializer = SurveyResponseSerializer(survey_response)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AcademySurveyResponseView(APIView, HeaderLimitOffsetPagination, GenerateLookupsMixin):
    """
    Staff endpoint to list survey responses for an academy with filters.

    Query params (all optional):
    - user: user id (supports comma-separated values for bulk filter)
    - survey_config: SurveyConfiguration id (supports comma-separated values)
    - cohort_id: Cohort id (stored in trigger_context)
    - status: PENDING|ANSWERED|EXPIRED (supports comma-separated values)
    """

    @capable_of("read_survey")
    def get(self, request, academy_id=None, response_id=None):
        if response_id is not None:
            item = SurveyResponse.objects.filter(
                id=response_id, survey_config__academy__id=academy_id
            ).first()
            if not item:
                raise NotFound("Survey response not found")

            serializer = SurveyResponseSerializer(item)
            return Response(serializer.data, status=status.HTTP_200_OK)

        items = SurveyResponse.objects.filter(survey_config__academy__id=academy_id)

        # Relationships-based filters (user, survey_config)
        lookups = self.generate_lookups(request, relationships=["user", "survey_config"], many_relationships=["user", "survey_config"])
        if lookups:
            items = items.filter(**lookups)

        # Status filter (comma-separated)
        status_param = request.GET.get("status")
        if status_param:
            statuses = [x.strip().upper() for x in status_param.split(",") if x.strip()]
            items = items.filter(status__in=statuses)

        # Cohort filter (from trigger_context)
        cohort_id = request.GET.get("cohort_id") or request.GET.get("cohort")
        cohort_ids = request.GET.get("cohort_ids")

        if cohort_ids:
            values = [x.strip() for x in cohort_ids.split(",") if x.strip()]
            if not all(v.isdigit() for v in values):
                raise ValidationException("cohort_ids must be integers", code=400, slug="invalid-cohort-ids")
            items = items.filter(trigger_context__cohort_id__in=[int(v) for v in values])

        elif cohort_id:
            if not str(cohort_id).isdigit():
                raise ValidationException("cohort_id must be an integer", code=400, slug="invalid-cohort-id")
            items = items.filter(trigger_context__cohort_id=int(cohort_id))

        items = items.order_by("-created_at")

        page = self.paginate_queryset(items, request)
        if page is not None:
            serializer = SurveyResponseSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = SurveyResponseSerializer(items, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)