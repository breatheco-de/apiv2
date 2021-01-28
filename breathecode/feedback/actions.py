from breathecode.notify.actions import send_email_message, send_slack
import logging, random
from breathecode.utils import ValidationException
from breathecode.authenticate.actions import create_token
from breathecode.authenticate.models import Token
from .models import Answer, Survey
from breathecode.admissions.models import CohortUser

logger = logging.getLogger(__name__)

strings = {
    "es": {
        "event": {
            "title": "¿Que tan probable es que recomiendes eventos como estos a tus familiares y amigos?",
            "highest": "muy probable",
            "lowest": "poco probable",
        },
        "mentor": {
            "title": "¿Como ha sido tu experiencia con tu mentor {}?",
            "highest": "muy buena",
            "lowest": "mala",
        },
        "cohort": {
            "title": "¿Cómo ha sido tu experiencia estudiando {}?",
            "highest": "muy buena",
            "lowest": "mala",
        },
        "academy": {
            "title": "¿Qué tan probable es que recomiendes {} a tus amigos y familiares?",
            "highest": "muy probable",
            "lowest": "poco probable",
        },
        "button_label": "Responder",
        "survey_subject": "Necesitamos tu feedback",
        "survey_message": "Por favor toma 5 minutos para enviarnos un feedback sobre tu experiencia en la academia hasta ahora",
    },
    "en": {
        "event": {
            "title": "How likely are you to recommend upcomint events to your friends and family?",
            "highest": "very likely",
            "lowest": "not likely",
        },
        "mentor": {
            "title": "How has been your experience with your mentor {} so far?",
            "highest": "very good",
            "lowest": "not good",
        },
        "cohort": {
            "title": "How has been your experience studying {} so far?",
            "highest": "very good",
            "lowest": "not good",
        },
        "academy": {
            "title": "How likely are you to recommend {} to your friends and family?",
            "highest": "very likely",
            "lowest": "not likely",
        },
        "button_label": "Answer the question",
        "survey_subject": "We need your feedback",
        "survey_message": "Please take 5 minutes to give us feedback about your experience at the academy so far.",
    }
}

def build_question(answer):

    question = { "title": "", "lowest": "", "highest": "" }
    if answer.event is not None:
        question["title"] = strings[answer.lang]["event"]["title"]
        question["lowest"] = strings[answer.lang]["event"]["lowest"]
        question["highest"] = strings[answer.lang]["event"]["highest"]
    elif answer.mentor is not None:
        question["title"] = strings[answer.lang]["mentor"]["title"].format(answer.mentor.first_name + " " + answer.mentor.last_name)
        question["lowest"] = strings[answer.lang]["mentor"]["lowest"]
        question["highest"] = strings[answer.lang]["mentor"]["highest"]
    elif answer.cohort is not None:
        question["title"] = strings[answer.lang]["cohort"]["title"].format(answer.cohort.certificate.name)
        question["lowest"] = strings[answer.lang]["cohort"]["lowest"]
        question["highest"] = strings[answer.lang]["cohort"]["highest"]
    elif answer.academy is not None:
        question["title"] = strings[answer.lang]["academy"]["title"].format(answer.academy.name)
        question["lowest"] = strings[answer.lang]["academy"]["lowest"]
        question["highest"] = strings[answer.lang]["academy"]["highest"]

    return question

def send_survey_group(survey=None,cohort=None):
    if survey is None and cohort is None:
        raise ValidationException('Missing survey or cohort')

    if survey is None:
        survey = Survey(cohort = cohort, lang=cohort.language)
    elif cohort is not None:
        if survey.cohort.id != cohort.id:
            raise ValidationException("The survey does not match the cohort id")

    if cohort is None:
        cohort = survey.cohort

    ucs = CohortUser.objects.filter(cohort=cohort).filter()
    for uc in ucs:
        user = uc.user
        has_slackuser = hasattr(user, 'slackuser')
        if not user.email and not has_slackuser:
            message = f'Author not have email and slack, this survey cannot be send by {str(user.id)}'
            logger.info(message)
            raise Exception(message)
        
        token = create_token(user, hours_length=48)
        data = {
            "SUBJECT": strings[cohort.language]["survey_subject"],
            "MESSAGE": strings[cohort.language]["survey_message"],
            "SURVEY_ID": survey.id,
            "BUTTON": strings[cohort.language]["button_label"],
            "LINK": f"https://nps.breatheco.de/survey/{survey.id}?token={token.key}",
        }

        if user.email:
            send_email_message("nps_survey", user.email, data)

        if hasattr(user, 'slackuser') and hasattr(cohort.academy, 'slackteam'):
            send_slack("nps_survey", user.slackuser, cohort.academy.slackteam, data=data)

def send_question(user, cohort=None):
    answer = Answer(user = user)
    if cohort is not None: 
        answer.cohort = cohort
    else:
        cohorts = CohortUser.objects.filter(user__id=user.id).order_by("-cohort__kickoff_date")
        _count = cohorts.count()
        if _count == 1:
            _cohort = cohorts.first().cohort
            answer.cohort = _cohort
    
    if answer.cohort is None:
        message = 'Impossible to determine the student cohort, maybe it has more than one, or cero.'
        logger.info(message)
        raise Exception(message)
    else:
        answer.lang = answer.cohort.language
        answer.save()

    has_slackuser = hasattr(user, 'slackuser')

    if not user.email and not has_slackuser:
        message = f'User not have email and slack, this survey cannot be send: {str(user.id)}'
        logger.info(message)
        raise Exception(message)

    question_was_sent_previously = Answer.objects.filter(cohort=answer.cohort, user=user,
        status='SENT').count()

    question = build_question(answer)

    if question_was_sent_previously:
        answer = Answer.objects.filter(cohort=answer.cohort, user=user, status='SENT').first()
        Token.objects.filter(id=answer.token_id).delete()

    else:
        answer.title = question["title"]
        answer.lowest = question["lowest"]
        answer.highest = question["highest"]
        answer.lang = answer.cohort.language
        answer.save()

    token = create_token(user, hours_length=48)

    token_id = Token.objects.filter(key=token).values_list('id', flat=True).first()
    answer.token_id = token_id
    answer.save()

    data = {
        "QUESTION": question,
        "HIGHEST": answer.highest,
        "LOWEST": answer.lowest,
        "SUBJECT": question,
        "ANSWER_ID": answer.id,
        "BUTTON": strings[answer.cohort.language]["button_label"],
        "LINK": f"https://nps.breatheco.de/{answer.id}?token={token.key}",
    }

    if user.email:
        send_email_message("nps", user.email, data)

    if hasattr(user, 'slackuser') and hasattr(answer.cohort.academy, 'slackteam'):
        send_slack("nps", user.slackuser, answer.cohort.academy.slackteam, data=data)
    
    # keep track of sent survays until they get answered
    if not question_was_sent_previously:
        logger.info(f"Survey was sent for user: {str(user.id)}")
        answer.status = "SENT"
        answer.save()
        return True

    else:
        logger.info(f"Survey was resent for user: {str(user.id)}")
        return True


def answer_survey(user, data):
    answer = Answer.objects.create(**{ **data, "user": user })

    # log = SurveyLog.objects.filter(
    #     user__id=user.id, 
    #     cohort__id=answer.cohort.id, 
    #     academy__id=answer.academy.id,
    #     mentor__id=answer.academy.id
    # )