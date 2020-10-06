from breathecode.notify.actions import send_email_message
from breathecode.authenticate.actions import create_token

strings = {
    "es": {
        "question": "¿Qué tan probable es que recomiendes 4Geeks Academy a tus amigos y familiares?"
    },
    "us": {
        "question": "How likely are you to recomend 4Geeks Academy to your friends and family?"
    }
}

def send_survey(user, cohort=None):

    question = strings["us"]["question"]
    if cohort is not None: 
        question = strings[cohort.language]["question"]

    token = create_token(user, hours_length=48)

    data = {
        "QUESTION": question,
        "LINK": "https://nps.breatheco.de/?token="+token.key
    }

    send_email_message("nps", user.email, data)