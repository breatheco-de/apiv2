from breathecode.notify.actions import send_email_message, send_slack
import logging
from breathecode.authenticate.actions import create_token
from breathecode.authenticate.models import Token
from .models import Answer
from breathecode.admissions.models import CohortUser

logger = logging.getLogger(__name__)

strings = {
    "es": {
        "first": "¿Qué tan probable es que recomiendes",
        "second": "a tus amigos y familiares?",
        "highest": "muy probable",
        "lowest": "no es probable",
        "button_label": "Responder",
    },
    "en": {
        "first": "How likely are you to recommend",
        "second": "to your friends and family?",
        "highest": "very likely",
        "lowest": "not likely",
        "button_label": "Answer the question",
    }
}

def send_survey(user, cohort=None):
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

    has_slackuser = hasattr(user, 'slackuser')

    if not user.email and not has_slackuser:
        message = f'User not have email and slack, this survey cannot be send: {str(user.id)}'
        logger.info(message)
        raise Exception(message)

    question_was_sent_previously = Answer.objects.filter(cohort=answer.cohort, user=user,
        status='SENT').count()

    question = (f'{strings[answer.cohort.language]["first"]} {answer.cohort.academy.name} '
        f'{strings[answer.cohort.language]["second"]}')

    if question_was_sent_previously:
        answer = Answer.objects.filter(cohort=answer.cohort, user=user, status='SENT').first()
        Token.objects.filter(id=answer.token_id).delete()

    else:
        answer.academy = answer.cohort.academy
        answer.title = question
        answer.lowest = strings[answer.cohort.language]["lowest"]
        answer.highest = strings[answer.cohort.language]["highest"]
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