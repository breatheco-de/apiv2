from datetime import datetime

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from breathecode.admissions.models import Academy
from breathecode.authenticate.actions import get_user_language
from breathecode.marketing.serializers import FormEntryBigSerializer, PostFormEntrySerializer
from breathecode.marketing.tasks import persist_single_lead
from breathecode.utils import APIViewExtensions, GenerateLookupsMixin, capable_of
from breathecode.utils.i18n import translation
from capyc.rest_framework.exceptions import ValidationException

from .models import Answer, Assessment, AssessmentLayout, AssessmentThreshold, Option, Question, UserAssessment
from .serializers import (
    AnswerSerializer,
    AnswerSmallSerializer,
    AssessmentPUTSerializer,
    GetAssessmentBigSerializer,
    GetAssessmentLayoutSerializer,
    GetAssessmentSerializer,
    GetAssessmentThresholdSerializer,
    GetUserAssessmentSerializer,
    OptionSerializer,
    PostUserAssessmentSerializer,
    PublicUserAssessmentSerializer,
    PUTUserAssessmentSerializer,
    QuestionSerializer,
    SmallUserAssessmentSerializer,
)


class TrackAssessmentView(APIView, GenerateLookupsMixin):
    """
    List all snippets, or create a new snippet.
    """

    permission_classes = [AllowAny]

    def get(self, request, ua_token):
        lang = get_user_language(request)
        now = timezone.now()

        single = UserAssessment.objects.filter(token=ua_token).first()
        if single is None or now > single.created_at + single.assessment.max_session_duration:
            raise ValidationException(
                translation(
                    lang,
                    en="User assessment session does not exist or has already expired",
                    es="Esta sessión de evaluación no existe o ya ha expirado",
                    slug="not-found",
                ),
                code=404,
            )

        serializer = PublicUserAssessmentSerializer(single, many=False)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, ua_token):
        lang = get_user_language(request)
        ass = UserAssessment.objects.filter(token=ua_token).first()
        if not ass:
            raise ValidationException("User Assessment not found", 404)

        serializer = PUTUserAssessmentSerializer(ass, data=request.data, context={"request": request, "lang": lang})
        if serializer.is_valid():
            serializer.save()
            serializer = GetUserAssessmentSerializer(serializer.instance)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request):

        lang = get_user_language(request)
        payload = request.data.copy()
        serializer = PostUserAssessmentSerializer(data=payload, context={"request": request, "lang": lang})
        if serializer.is_valid():
            serializer.save()
            serializer = GetUserAssessmentSerializer(serializer.instance)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GetAssessmentView(APIView):
    """
    List all snippets, or create a new snippet.
    """

    permission_classes = [AllowAny]

    def get(self, request, assessment_slug=None):

        if assessment_slug is not None:
            lang = None
            if "lang" in self.request.GET:
                lang = self.request.GET.get("lang")

            item = Assessment.objects.filter(slug=assessment_slug, is_archived=False).first()
            if item is None:
                raise ValidationException("Assessment not found or its archived", 404)

            if lang is not None and item.lang != lang:
                item = item.translations.filter(lang=lang).first()
                if item is None:
                    raise ValidationException(f"Language '{lang}' not found for assesment {assessment_slug}", 404)

            serializer = GetAssessmentBigSerializer(item, many=False)
            return Response(serializer.data, status=status.HTTP_200_OK)

        # get original all assessments (assessments that have no parent)
        items = Assessment.objects.all()
        lookup = {}

        if "academy" in self.request.GET:
            param = self.request.GET.get("academy")
            lookup["academy__id"] = param

        if "lang" in self.request.GET:
            param = self.request.GET.get("lang")
            lookup["lang"] = param

        # user can specify include_archived on querystring to include archived assessments
        if not "include_archived" in self.request.GET or self.request.GET.get("include_archived") != "true":
            lookup["is_archived"] = False

        if "no_asset" in self.request.GET and self.request.GET.get("no_asset").lower() == "true":
            lookup["asset__isnull"] = True

        if "author" in self.request.GET:
            param = self.request.GET.get("author")
            lookup["author__id"] = param

        items = items.filter(**lookup).order_by("-created_at")

        serializer = GetAssessmentSerializer(items, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @capable_of("crud_assessment")
    def put(self, request, assessment_slug=None, academy_id=None):

        lang = get_user_language(request)

        _assessment = Assessment.objects.filter(slug=assessment_slug, academy__id=academy_id, is_archived=False).first()
        if _assessment is None:
            raise ValidationException(
                translation(
                    lang,
                    en=f"Assessment {assessment_slug} not found or its archived for academy {academy_id}",
                    es=f"La evaluación {assessment_slug} no se encontró o esta archivada para la academia {academy_id}",
                    slug="not-found",
                )
            )

        all_serializers = []
        assessment_serializer = AssessmentPUTSerializer(
            _assessment, data=request.data, context={"request": request, "academy": academy_id, "lang": lang}
        )
        if not assessment_serializer.is_valid():
            return Response(assessment_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        all_serializers.append(assessment_serializer)

        question_index = 0
        if "questions" in request.data:
            for q in request.data["questions"]:
                question_index += 1

                q_serializer = None
                if "id" in q:
                    question = Question.objects.filter(id=q["id"], assessment=_assessment).first()
                    if question is None:
                        raise ValidationException(
                            translation(
                                lang,
                                en=f'Question {q["id"]} not found for this assessment',
                                es=f'No se ha encontrado esta pregunta {q["id"]} dentro del assessment',
                                slug="not-found",
                            )
                        )

                    q_serializer = QuestionSerializer(question, data=q)

                if "title" in q and q_serializer is None:
                    question = Question.objects.filter(title=q["title"], assessment=_assessment).first()
                    if question is not None:
                        q_serializer = QuestionSerializer(question, data=q)

                if q_serializer is None:
                    q_serializer = QuestionSerializer(data=q)

                all_serializers.append(q_serializer)
                if not q_serializer.is_valid():
                    return Response(assessment_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

                total_score = 0
                if "options" in q:
                    for opt in q["options"]:

                        opt_serializer = None
                        if "id" in opt:
                            option = Option.objects.filter(id=opt["id"], question=question).first()
                            if option is None:
                                raise ValidationException(
                                    translation(
                                        lang,
                                        en=f'Option {opt["id"]} not found on this question',
                                        es=f'No se ha encontrado la opcion {opt["id"]} en esta pregunta',
                                        slug="not-found",
                                    )
                                )

                            opt_serializer = OptionSerializer(option, data=opt)

                        if "title" in opt and opt_serializer is None:
                            option = Option.objects.filter(title=opt["title"], question=question).first()
                            if option is not None:
                                opt_serializer = OptionSerializer(option, data=opt)

                        if opt_serializer is None:
                            opt_serializer = OptionSerializer(data=opt)

                        all_serializers.append(opt_serializer)
                        if not opt_serializer.is_valid():
                            return Response(opt_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

                        score = float(opt["score"]) if "score" in opt else float(opt_serializer.data["score"])
                        if score > 0:
                            total_score += score

                if total_score <= 0:
                    raise ValidationException(
                        translation(
                            lang,
                            en=f"Question {question_index} total score must be allowed to be bigger than 0",
                            es=f"El score de la pregunta {question_index} debe poder ser mayor a 0",
                            slug="bigger-than-cero",
                        )
                    )

            first_instance = None
            question_to_assign = None
            for s in all_serializers:
                _ins = s.save()

                # lets save the assessment instance to return it to the front end
                if first_instance is None:
                    first_instance = _ins

                # Assign question to the nearest options
                if isinstance(_ins, Question):
                    _ins.assessment = _assessment
                    _ins.save()
                    question_to_assign = _ins

                # if its an option we assign the question to it
                if isinstance(_ins, Option) and question_to_assign:
                    _ins.question = question_to_assign
                    _ins.save()

            return Response(GetAssessmentBigSerializer(first_instance).data, status=status.HTTP_200_OK)
        return Response(assessment_serializer.data, status=status.HTTP_200_OK)


class AssessmentLayoutView(APIView):
    """
    List all snippets, or create a new snippet.
    """

    permission_classes = [AllowAny]

    def get(self, request, layout_slug):

        item = AssessmentLayout.objects.filter(slug=layout_slug).first()
        if item is None:
            raise ValidationException("Assessment layout not found", 404)
        serializer = GetAssessmentLayoutSerializer(item, many=False)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AcademyAssessmentLayoutView(APIView):
    """
    List all snippets, or create a new snippet.
    """

    permission_classes = [AllowAny]

    @capable_of("read_assessment")
    def get(self, request, academy_id, layout_slug=None):

        if layout_slug:
            item = AssessmentLayout.objects.filter(slug=layout_slug, academy__id=academy_id).first()
            if item is None:
                raise ValidationException("Assessment layout not found for this academy", 404)
            serializer = GetAssessmentLayoutSerializer(item)
            return Response(serializer.data, status=status.HTTP_200_OK)

        # get original all assessments (assessments that have no parent)
        items = AssessmentLayout.objects.filter(academy__id=academy_id)
        lookup = {}

        # if 'academy' in self.request.GET:
        #     param = self.request.GET.get('academy')
        #     lookup['academy__isnull'] = True

        items = items.filter(**lookup).order_by("-created_at")

        serializer = GetAssessmentLayoutSerializer(items, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([AllowAny])
def create_public_assessment(request):
    data = request.data.copy()

    # remove spaces from phone
    if "phone" in data:
        data["phone"] = data["phone"].replace(" ", "")

    serializer = PostFormEntrySerializer(data=data)
    if serializer.is_valid():
        serializer.save()

        persist_single_lead.delay(serializer.data)

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AssessmentOptionView(APIView):

    @capable_of("crud_assessment")
    def delete(self, request, assessment_slug, option_id=None, academy_id=None):

        lang = get_user_language(request)

        option = Option.objects.filter(id=option_id, question__assessment__slug=assessment_slug).first()
        if option is None:
            raise ValidationException(
                translation(
                    lang,
                    en=f"Option {option_id} not found on assessment {assessment_slug}",
                    es=f"Option de pregunta {option_id} no encontrada para el assessment {assessment_slug}",
                    slug="not-found",
                )
            )

        if option.question.option_set.filter(is_deleted=False).count() <= 2:
            raise ValidationException(
                translation(
                    lang,
                    en=f"Question {option.question.id} needs at least 2 options",
                    es=f"La pregunta {option.question.id} necesita al menos dos opciones",
                    slug="at-least-two",
                )
            )

        if option.answer_set.count() > 0:
            option.is_deleted = True
            option.save()
        else:
            option.delete()

        return Response(None, status=status.HTTP_204_NO_CONTENT)


class AssessmentQuestionView(APIView):

    @capable_of("crud_assessment")
    def delete(self, request, assessment_slug, question_id=None, academy_id=None):

        lang = get_user_language(request)

        question = Question.objects.filter(id=question_id, assessment__slug=assessment_slug).first()
        if question is None:
            raise ValidationException(
                translation(
                    lang,
                    en=f"Question {question_id} not found on assessment {assessment_slug}",
                    es=f"La pregunta {question_id} no fue encontrada para el assessment {assessment_slug}",
                    slug="not-found",
                )
            )

        if question.assessment.question_set.filter(is_deleted=False).count() <= 2:
            raise ValidationException(
                translation(
                    lang,
                    en=f"Assessment {assessment_slug} needs at least 2 questions",
                    es=f"La evaluación {assessment_slug} necesita al menos dos preguntas",
                    slug="at-least-two",
                )
            )

        if question.answer_set.count() > 0:
            question.is_deleted = True
            question.save()
        else:
            question.delete()

        return Response(None, status=status.HTTP_204_NO_CONTENT)


class GetThresholdView(APIView):
    """
    List all snippets, or create a new snippet.
    """

    permission_classes = [AllowAny]

    def get(self, request, assessment_slug, threshold_id=None):

        item = Assessment.objects.filter(slug=assessment_slug).first()
        if item is None:
            raise ValidationException("Assessment not found", 404)

        if threshold_id is not None:
            single = AssessmentThreshold.objects.filter(id=threshold_id, assessment__slug=assessment_slug).first()
            if single is None:
                raise ValidationException(f"Threshold {threshold_id} not found", 404, slug="threshold-not-found")

            serializer = GetAssessmentThresholdSerializer(single, many=False)
            return Response(serializer.data, status=status.HTTP_200_OK)

        # get original all assessments (assessments that have no parent)
        items = AssessmentThreshold.objects.filter(assessment__slug=assessment_slug)
        lookup = {}

        if "academy" in self.request.GET:
            param = self.request.GET.get("academy")

            if param.isnumeric():
                lookup["academy__id"] = int(param)
            else:
                lookup["academy__slug"] = param
        else:
            lookup["academy__isnull"] = True

        if "tag" in self.request.GET:
            param = self.request.GET.get("tags")
            if param != "all":
                lookup["tags__icontains"] = param
        else:
            lookup["tags__in"] = ["", None]

        items = items.filter(**lookup).order_by("-created_at")

        serializer = GetAssessmentThresholdSerializer(items, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AcademyUserAssessmentView(APIView, GenerateLookupsMixin):
    """
    List all snippets, or create a new snippet.
    """

    extensions = APIViewExtensions(sort="-created_at", paginate=True)

    @capable_of("read_user_assessment")
    def get(self, request, academy_id=None, ua_id=None):
        handler = self.extensions(request)

        if ua_id is not None:
            single = UserAssessment.objects.filter(id=ua_id, academy__id=academy_id).first()
            if single is None:
                raise ValidationException(f"UserAssessment {ua_id} not found", 404, slug="user-assessment-not-found")

            serializer = GetUserAssessmentSerializer(single, many=False)
            return handler.response(serializer.data)

        items = UserAssessment.objects.filter(academy__id=academy_id)
        lookup = {}

        start = request.GET.get("started_at", None)
        if start is not None:
            start_date = datetime.datetime.strptime(start, "%Y-%m-%d").date()
            lookup["started_at__gte"] = start_date

        end = request.GET.get("finished_at", None)
        if end is not None:
            end_date = datetime.datetime.strptime(end, "%Y-%m-%d").date()
            lookup["finished_at__lte"] = end_date

        if "status" in self.request.GET:
            param = self.request.GET.get("status")
            lookup["status"] = param

        if "opened" in self.request.GET:
            param = self.request.GET.get("opened")
            lookup["opened"] = param == "true"

        if "course" in self.request.GET:
            param = self.request.GET.get("course")
            lookup["course__in"] = [x.strip() for x in param.split(",")]

        if "owner" in self.request.GET:
            param = self.request.GET.get("owner")
            lookup["owner__id"] = param
        elif "owner_email" in self.request.GET:
            param = self.request.GET.get("owner_email")
            lookup["owner_email"] = param

        if "lang" in self.request.GET:
            param = self.request.GET.get("lang")
            lookup["lang"] = param

        items = items.filter(**lookup)
        items = handler.queryset(items)

        serializer = SmallUserAssessmentSerializer(items, many=True)
        return handler.response(serializer.data)

    @capable_of("crud_user_assessment")
    def post(self, request, academy_id=None):

        academy = Academy.objects.filter(id=academy_id).first()
        if academy is None:
            raise ValidationException(f"Academy {academy_id} not found", slug="academy-not-found")

        # ignore the incoming location information and override with the session academy
        data = {**request.data, "location": academy.active_campaign_slug}

        serializer = PostFormEntrySerializer(data=data, context={"request": request, "academy": academy_id})
        if serializer.is_valid():
            serializer.save()
            big_serializer = FormEntryBigSerializer(serializer.instance)
            return Response(big_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AcademyAnswerView(APIView, GenerateLookupsMixin):
    """
    List all snippets, or create a new snippet.
    """

    extensions = APIViewExtensions(sort="-created_at", paginate=True)

    @capable_of("read_user_assessment")
    def get(self, request, academy_id, ua_id=None, answer_id=None):
        handler = self.extensions(request)

        if answer_id is not None:
            single = Answer.objects.filter(
                id=answer_id, user_assessment__id=ua_id, user_assessment__academy__id=academy_id
            ).first()
            if single is None:
                raise ValidationException(
                    f"Answer {answer_id} not found on user assessment {ua_id}", 404, slug="answer-not-found"
                )

            serializer = AnswerSmallSerializer(single, many=False)
            return handler.response(serializer.data)

        items = Answer.objects.filter(user_assessment__id=ua_id, user_assessment__academy__id=academy_id)
        lookup = {}

        start = request.GET.get("starting_at", None)
        if start is not None:
            start_date = datetime.strptime(start, "%Y-%m-%d").date()
            lookup["created_at__gte"] = start_date

        end = request.GET.get("ending_at", None)
        if end is not None:
            end_date = datetime.strptime(end, "%Y-%m-%d").date()
            lookup["created_at__lte"] = end_date

        if "user_assessments" in self.request.GET:
            param = self.request.GET.get("user_assessments")
            lookup["user_assessment__id__in"] = [x.strip() for x in param.split(",")]

        if "assessments" in self.request.GET:
            param = self.request.GET.get("assessments")
            lookup["question__assessment__id__in"] = [x.strip() for x in param.split(",")]

        if "questions" in self.request.GET:
            param = self.request.GET.get("questions")
            lookup["question__id__in"] = [x.strip() for x in param.split(",")]

        if "options" in self.request.GET:
            param = self.request.GET.get("options")
            lookup["option__id__in"] = [x.strip() for x in param.split(",")]

        if "owner" in self.request.GET:
            param = self.request.GET.get("owner")
            lookup["user_assessments__owner__id__in"] = [x.strip() for x in param.split(",")]

        elif "owner_email" in self.request.GET:
            param = self.request.GET.get("owner_email")
            lookup["owner_email"] = param

        if "lang" in self.request.GET:
            param = self.request.GET.get("lang")
            lookup["user_assessments__lang"] = param

        items = items.filter(**lookup)
        items = handler.queryset(items)

        serializer = AnswerSmallSerializer(items, many=True)
        return handler.response(serializer.data)


class AnswerView(APIView, GenerateLookupsMixin):
    """
    List all snippets, or create a new snippet.
    """

    permission_classes = [AllowAny]

    extensions = APIViewExtensions(sort="-created_at", paginate=True)

    def get(self, request, token, answer_id=None):
        handler = self.extensions(request)

        if answer_id is not None:
            single = Answer.objects.filter(id=answer_id, user_assessment__token=token).first()
            if single is None:
                raise ValidationException(
                    f"Answer {answer_id} not found on user assessment", 404, slug="answer-not-found"
                )

            serializer = AnswerSmallSerializer(single, many=False)
            return handler.response(serializer.data)

        items = Answer.objects.filter(user_assessment__token=token)
        lookup = {}

        if "questions" in self.request.GET:
            param = self.request.GET.get("questions")
            lookup["question__id__in"] = [x.strip() for x in param.split(",")]

        if "options" in self.request.GET:
            param = self.request.GET.get("options")
            lookup["option__id__in"] = [x.strip() for x in param.split(",")]

        items = items.filter(**lookup)
        items = handler.queryset(items)

        serializer = AnswerSmallSerializer(items, many=True)
        return handler.response(serializer.data)

    def post(self, request, token):

        lang = get_user_language(request)

        data = {
            **request.data,
            "token": token,
        }
        serializer = AnswerSerializer(data=data, context={"request": request, "lang": lang})
        if serializer.is_valid():
            serializer.save()
            big_serializer = AnswerSmallSerializer(serializer.instance)
            return Response(big_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, token, answer_id=None):

        lang = get_user_language(request)
        lookups = self.generate_lookups(request, many_fields=["id"])

        if lookups and answer_id:
            raise ValidationException(
                translation(
                    lang,
                    en="answer_id must not be provided by url if deleting in bulk",
                    es="El answer_id no debe ser enviado como parte del path si se quiere una eliminacion masiva",
                    slug="bulk-querystring",
                )
            )

        uass = UserAssessment.objects.filter(token=token).first()
        if not uass:
            raise ValidationException(
                translation(
                    lang,
                    en="user assessment not found for this token",
                    es="No se han encontrado un user assessment con ese token",
                    slug="not-found",
                )
            )

        if lookups:
            items = Answer.objects.filter(**lookups, user_assessment=uass)

            for item in items:
                item.delete()

            return Response(None, status=status.HTTP_204_NO_CONTENT)

        if answer_id is None:
            raise ValidationException("Missing answer_id", code=400)

        ans = Answer.objects.filter(id=answer_id, user_assessment=uass).first()
        if ans is None:
            raise ValidationException("Specified answer and token could not be found")

        ans.delete()
        return Response(None, status=status.HTTP_204_NO_CONTENT)
