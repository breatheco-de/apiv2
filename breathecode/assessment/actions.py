from breathecode.notify.actions import send_email_message
import logging
from breathecode.authenticate.actions import create_token
from .models import StudentAssessment

logger = logging.getLogger(__name__)

def send_assestment(student_assessment):

    token = create_token(student_assessment.user, hours_length=48)
    data = {
        "SUBJECT": student_assessment.assessment.title,
        "LINK": f"https://assessment.breatheco.de/{student_assessment.id}?token={token.key}"
    }
    send_email_message("assessment", student_assessment.user.email, data)
    
    logger.info(f"Survey was sent for user: {str(student_assessment.user.id)}")
    
    student_assessment.status = "SENT"
    student_assessment.save()

    return True
    # keep track of sent survays until they get answered


# def answer_survey(user, data):
#     answer = Answer.objects.create(**{ **data, "user": user })

    # log = SurveyLog.objects.filter(
    #     user__id=user.id, 
    #     cohort__id=answer.cohort.id, 
    #     academy__id=answer.academy.id,
    #     mentor__id=answer.academy.id
    # )