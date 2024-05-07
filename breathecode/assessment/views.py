from django.http import HttpResponse
from django.utils import timezone
from PIL import Image
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from breathecode.authenticate.actions import get_user_language
from breathecode.utils import capable_of
from breathecode.utils.i18n import translation
from capyc.rest_framework.exceptions import ValidationException

from .models import Assessment, AssessmentThreshold, Option, Question, UserAssessment
from .serializers import (
    AssessmentPUTSerializer,
    GetAssessmentBigSerializer,
    GetAssessmentSerializer,
    GetAssessmentThresholdSerializer,
    OptionSerializer,
    QuestionSerializer,
)


@api_view(['GET'])
@permission_classes([AllowAny])
def track_assesment_open(request, user_assessment_id=None):

    ass = UserAssessment.objects.filter(id=user_assessment_id, status='SENT').first()
    if ass is not None:
        ass.status = 'OPENED'
        ass.opened_at = timezone.now()
        ass.save()

    image = Image.new('RGB', (1, 1))
    response = HttpResponse(content_type='image/png')
    image.save(response, 'PNG')
    return response


class GetAssessmentView(APIView):
    """
    List all snippets, or create a new snippet.
    """
    permission_classes = [AllowAny]

    def get(self, request, assessment_slug=None):

        if assessment_slug is not None:
            lang = None
            if 'lang' in self.request.GET:
                lang = self.request.GET.get('lang')

            item = Assessment.objects.filter(slug=assessment_slug).first()
            if item is None:
                raise ValidationException('Assessment not found', 404)

            if lang is not None and item.lang != lang:
                item = item.translations.filter(lang=lang).first()
                if item is None:
                    raise ValidationException(f"Language '{lang}' not found for assesment {assessment_slug}", 404)

            serializer = GetAssessmentBigSerializer(item, many=False)
            return Response(serializer.data, status=status.HTTP_200_OK)

        # get original all assessments (assessments that have no parent)
        items = Assessment.objects.all()
        lookup = {}

        if 'academy' in self.request.GET:
            param = self.request.GET.get('academy')
            lookup['academy__id'] = param

        if 'lang' in self.request.GET:
            param = self.request.GET.get('lang')
            lookup['lang'] = param

        if 'no_asset' in self.request.GET and self.request.GET.get('no_asset').lower() == 'true':
            lookup['asset__isnull'] = True

        if 'author' in self.request.GET:
            param = self.request.GET.get('author')
            lookup['author__id'] = param

        items = items.filter(**lookup).order_by('-created_at')

        serializer = GetAssessmentSerializer(items, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @capable_of('crud_assessment')
    def put(self, request, assessment_slug=None, academy_id=None):

        lang = get_user_language(request)

        _assessment = Assessment.objects.filter(slug=assessment_slug, academy__id=academy_id).first()
        if _assessment is None:
            raise ValidationException(
                translation(lang,
                            en=f'Assessment {assessment_slug} not found for academy {academy_id}',
                            es=f'La evaluación {assessment_slug} no se encontró para la academia {academy_id}',
                            slug='not-found'))

        all_serializers = []
        assessment_serializer = AssessmentPUTSerializer(_assessment,
                                                        data=request.data,
                                                        context={
                                                            'request': request,
                                                            'academy': academy_id,
                                                            'lang': lang
                                                        })
        if not assessment_serializer.is_valid():
            return Response(assessment_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        all_serializers.append(assessment_serializer)

        question_index = 0
        if 'questions' in request.data:
            for q in request.data['questions']:
                question_index += 1

                q_serializer = None
                if 'id' in q:
                    question = Question.objects.filter(id=q['id'], assessment=_assessment).first()
                    if question is None:
                        raise ValidationException(
                            translation(lang,
                                        en=f'Question {q["id"]} not found for this assessment',
                                        es=f'No se ha encontrado esta pregunta {q["id"]} dentro del assessment',
                                        slug='not-found'))

                    q_serializer = QuestionSerializer(question, data=q)

                if 'title' in q and q_serializer is None:
                    question = Question.objects.filter(title=q['title'], assessment=_assessment).first()
                    if question is not None: q_serializer = QuestionSerializer(question, data=q)

                if q_serializer is None:
                    q_serializer = QuestionSerializer(data=q)

                all_serializers.append(q_serializer)
                if not q_serializer.is_valid():
                    return Response(assessment_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

                total_score = 0
                if 'options' in q:
                    for opt in q['options']:

                        opt_serializer = None
                        if 'id' in opt:
                            option = Option.objects.filter(id=opt['id'], question=question).first()
                            if option is None:
                                raise ValidationException(
                                    translation(lang,
                                                en=f'Option {opt["id"]} not found on this question',
                                                es=f'No se ha encontrado la opcion {opt["id"]} en esta pregunta',
                                                slug='not-found'))

                            opt_serializer = OptionSerializer(option, data=opt)

                        if 'title' in opt and opt_serializer is None:
                            option = Option.objects.filter(title=opt['title'], question=question).first()
                            if option is not None: opt_serializer = OptionSerializer(option, data=opt)

                        if opt_serializer is None:
                            opt_serializer = OptionSerializer(data=opt)

                        all_serializers.append(opt_serializer)
                        if not opt_serializer.is_valid():
                            return Response(opt_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

                        score = float(opt['score']) if 'score' in opt else float(opt_serializer.data['score'])
                        if score > 0: total_score += score

                if total_score <= 0:
                    raise ValidationException(
                        translation(lang,
                                    en=f'Question {question_index} total score must be allowed to be bigger than 0',
                                    es=f'El score de la pregunta {question_index} debe poder ser mayor a 0',
                                    slug='bigger-than-cero'))

            first_instance = None
            question_to_assign = None
            for s in all_serializers:
                _ins = s.save()

                # lets save the assessment instance to return it to the front end
                if first_instance is None: first_instance = _ins

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


class AssessmentOptionView(APIView):

    @capable_of('crud_assessment')
    def delete(self, request, assessment_slug, option_id=None, academy_id=None):

        lang = get_user_language(request)

        option = Option.objects.filter(id=option_id, question__assessment__slug=assessment_slug).first()
        if option is None:
            raise ValidationException(
                translation(lang,
                            en=f'Option {option_id} not found on assessment {assessment_slug}',
                            es=f'Option de pregunta {option_id} no encontrada para el assessment {assessment_slug}',
                            slug='not-found'))

        if option.question.option_set.filter(is_deleted=False).count() <= 2:
            raise ValidationException(
                translation(lang,
                            en=f'Question {option.question.id} needs at least 2 options',
                            es=f'La pregunta {option.question.id} necesita al menos dos opciones',
                            slug='at-least-two'))

        if option.answer_set.count() > 0:
            option.is_deleted = True
            option.save()
        else:
            option.delete()

        return Response(None, status=status.HTTP_204_NO_CONTENT)


class AssessmentQuestionView(APIView):

    @capable_of('crud_assessment')
    def delete(self, request, assessment_slug, question_id=None, academy_id=None):

        lang = get_user_language(request)

        question = Question.objects.filter(id=question_id, assessment__slug=assessment_slug).first()
        if question is None:
            raise ValidationException(
                translation(lang,
                            en=f'Question {question_id} not found on assessment {assessment_slug}',
                            es=f'La pregunta {question_id} no fue encontrada para el assessment {assessment_slug}',
                            slug='not-found'))

        if question.assessment.question_set.filter(is_deleted=False).count() <= 2:
            raise ValidationException(
                translation(lang,
                            en=f'Assessment {assessment_slug} needs at least 2 questions',
                            es=f'La evaluación {assessment_slug} necesita al menos dos preguntas',
                            slug='at-least-two'))

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

    def get(self, request, assessment_slug):

        item = Assessment.objects.filter(slug=assessment_slug).first()
        if item is None:
            raise ValidationException('Assessment not found', 404)

        # get original all assessments (assessments that have no parent)
        items = AssessmentThreshold.objects.filter(assessment__slug=assessment_slug)
        lookup = {}

        if 'academy' in self.request.GET:
            param = self.request.GET.get('academy')

            if param.isnumeric():
                lookup['academy__id'] = int(param)
            else:
                lookup['academy__slug'] = param
        else:
            lookup['academy__isnull'] = True

        items = items.filter(**lookup).order_by('-created_at')

        serializer = GetAssessmentThresholdSerializer(items, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
