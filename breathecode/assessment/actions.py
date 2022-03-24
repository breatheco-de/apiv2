from breathecode.authenticate.models import Token
from breathecode.notify.actions import send_email_message
from .models import Assessment, Question, Option
import logging

logger = logging.getLogger(__name__)


def create_from_json(payload: str):
    quiz = payload

    if quiz['info']['lang'] == 'en':
        quiz['info']['lang'] = 'us'

    if 'slug' not in quiz['info']:
        logger.log(f'Ignoring quiz because it does not have a slug')
        return None

    name = 'No name yet'
    if 'name' not in quiz['info']:
        logger.log(f"Quiz f{quiz['info']['slug']} needs a name")
    else:
        name = quiz['info']['name']

    a = Assessment.objects.filter(slug=quiz['info']['slug']).first()
    if a is not None:
        return None

    a = Assessment(
        slug=quiz['info']['slug'],
        lang=quiz['info']['lang'],
        title=name,
        comment=quiz['info']['main'],
    )
    a.save()

    for question in quiz['questions']:
        q = Question(
            title=question['q'],
            lang=quiz['info']['lang'],
            assessment=a,
            question_type='SELECT',
        )
        q.save()
        for option in question['a']:
            o = Option(
                title=option['option'],
                score=int(option['correct']),
                question=q,
            )
            o.save()
    return a


def send_assestment(user_assessment):

    token, created = Token.get_or_create(user_assessment.user, hours_length=48)
    data = {
        'SUBJECT': user_assessment.assessment.title,
        'LINK': f'https://assessment.breatheco.de/{user_assessment.id}?token={token.key}'
    }
    send_email_message('assessment', user_assessment.user.email, data)

    logger.info(f'Survey was sent for user: {str(user_assessment.user.id)}')

    user_assessment.status = 'SENT'
    user_assessment.save()

    return True
