from breathecode.notify.actions import send_email_message
from breathecode.authenticate.actions import create_token
from .models import Answer

strings = {
    "es": {
        "question": "¿Qué tan probable es que recomiendes 4Geeks Academy a tus amigos y familiares?"
    },
    "us": {
        "question": "How likely are you to recomend 4Geeks Academy to your friends and family?"
    }
}

def send_survey(user, cohort=None):

    answer = Answer(user = user)

    question = strings["us"]["question"]
    if cohort is not None: 
        question = strings[cohort.language]["question"]
        answer.cohort = cohort
    answer.save()

    token = create_token(user, hours_length=48)
    data = {
        "QUESTION": question,
        "SUBJECT": question,
        "LINK": f"https://nps.breatheco.de/{answer.id}?token={token.key}"
    }

    send_email_message("nps", user.email, data)

    answer.status = "SENT"
    answer.save()
    # keep track of sent survays until they get answered


def answer_survey(user, data):
    answer = Answer.objects.create(**{ **data, "user": user })

    # log = SurveyLog.objects.filter(
    #     user__id=user.id, 
    #     cohort__id=answer.cohort.id, 
    #     academy__id=answer.academy.id,
    #     mentor__id=answer.academy.id
    # )