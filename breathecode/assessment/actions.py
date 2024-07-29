import logging

from breathecode.authenticate.models import Token
from breathecode.notify.actions import send_email_message
from capyc.rest_framework.exceptions import ValidationException

from .models import Assessment, Option, Question

logger = logging.getLogger(__name__)


def validate_quiz_json(quiz, allow_override=False):

    if "info" not in quiz:
        raise ValidationException("Quiz is missing info json property")

    if "slug" not in quiz["info"]:
        raise ValidationException("Missing info.slug on quiz info")

    _result = {"questions": []}

    # We guarantee that "assessment" property will always be set to something (none or else)
    _result["assessment"] = Assessment.objects.filter(slug=quiz["info"]["slug"]).first()
    if not allow_override and _result["assessment"]:
        raise ValidationException(
            f"There is already an assessment (maybe it's archived) with slug {quiz['info']['slug']}, rename your quiz info.slug or delete the previous assessment"
        )

    if "id" in quiz:
        _result["id"] = quiz["id"]
    elif "id" in quiz["info"]:
        _result["id"] = quiz["info"]["id"]

    if "questions" not in quiz:
        raise Exception('Missing "questions" property in quiz')

    title = "Untitled assessment"
    if "name" in quiz["info"]:
        title = quiz["info"]["name"]
    if "title" in quiz["info"]:
        title = quiz["info"]["title"]

    _result["info"] = {
        "title": title,
        "slug": quiz["info"]["slug"],
    }

    _index = 0
    for question in quiz["questions"]:
        _index += 1

        _question = {"id": question["id"] if "id" in question else None}

        title = ""
        if "q" in question:
            title = question["q"]
        elif "title" in question:
            title = question["title"]
        else:
            raise Exception(f'Missing "title" property in quiz question #{_index}')

        _question["title"] = title

        options = []
        if "a" in question:
            options = question["a"]
        elif "answers" in question:
            options = question["answers"]
        elif "options" in question:
            options = question["options"]
        else:
            raise Exception('Missing "options" property in quiz question')

        _question["options"] = []

        o_index = 0
        for option in options:
            o_index += 1

            _id = None
            if "id" in option:
                _id = option["id"]

            title = "Untitled option"
            if "option" in option:
                title = option["option"]
            elif "title" in option:
                title = option["title"]
            else:
                raise Exception(f'Missing "title" property in option {str(o_index)}')

            score = 0
            if "correct" in option:
                score = option["correct"]
            elif "score" in option:
                score = option["score"]
            else:
                raise Exception(f'Missing "score" property in option {str(o_index)}')

            _question["options"].append({"id": _id, "title": title, "score": int(score)})

        _result["questions"].append(_question)

    return _result


def create_from_asset(asset, allow_override=False):

    if asset.academy is None:
        raise ValidationException(f"Asset {asset.slug} has not academy associated")

    if asset.assessment is not None and asset.assessment.asset_set.count() > 1:
        associated_assets = ",".join(asset.assessment.asset_set.all())
        raise ValidationException(
            "Assessment has more then one asset associated, please choose only one: " + associated_assets
        )

    quiz = validate_quiz_json(asset.config, allow_override)
    if asset.assessment is None:
        a = quiz["assessment"]
        if not a:
            a = Assessment.objects.create(
                title=quiz["info"]["title"],
                lang=asset.lang,
                slug=quiz["info"]["slug"],
                academy=asset.academy,
                author=asset.author,
            )

    if a is not None and a.question_set is not None and a.question_set.count() > 0:
        raise ValidationException(
            "Assessment already has questions, only empty assessments can by created from an asset"
        )

    a.save()

    for question in quiz["questions"]:

        q = None
        if question["id"]:
            q = Question.filter(id=question["id"]).first()
            if not q:
                raise ValidationException(f"Question with id {question['id']} not found for quiz {q.id}")

        if not q:
            q = Question(
                lang=asset.lang,
                assessment=a,
                question_type="SELECT",
            )

        q.title = question["title"]
        q.save()

        for option in question["options"]:
            o = None
            if option["id"]:
                o = Option.filter(id=option["id"]).first()
                if not o:
                    raise ValidationException(f"Option with id {option['id']} not found for question {q.id}")

            if not o:
                o = Option(question=q)

            o.title = option["title"]
            o.score = option["score"]
            o.save()

    asset.assessment = a
    asset.save()

    return asset


def send_assestment(user_assessment):

    token, created = Token.get_or_create(user_assessment.user, hours_length=48)
    data = {
        "SUBJECT": user_assessment.assessment.title,
        "LINK": f"https://assessment.4geeks.com/{user_assessment.id}?token={token.key}",
    }
    send_email_message("assessment", user_assessment.user.email, data)

    logger.info(f"Assessment was sent for user: {str(user_assessment.user.id)}")

    user_assessment.status = "SENT"
    user_assessment.save()

    return True
