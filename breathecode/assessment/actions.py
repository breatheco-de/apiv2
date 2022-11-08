from breathecode.authenticate.models import Token
from breathecode.notify.actions import send_email_message
from breathecode.utils.validation_exception import ValidationException
from .models import Assessment, Question, Option
import logging

logger = logging.getLogger(__name__)


def create_from_asset(asset):

    if asset.academy is None:
        raise ValidationException(f'Asset {asset.slug} has not academy associated')

    a = asset.assessment

    if asset.assessment is not None and asset.assessment.asset_set.count() > 1:
        associated_assets = ','.join(asset.assessment.asset_set.all())
        raise ValidationException(f'Assessment has more then one asset associated, please choose only one: ' +
                                  associated_assets)

    if asset.assessment is None:
        a = Assessment.objects.filter(slug=asset.slug).first()
        if a is not None:
            raise ValidationException(f'There is already an assessment with slug {asset.slug}')

        a = Assessment.objects.create(
            title=asset.title,
            lang=asset.lang,
            slug=asset.slug,
            academy=asset.academy,
            author=asset.author,
        )

    if a.question_set.count() > 0:
        raise ValidationException(
            f'Assessment already has questions, only empty assessments can by created from an asset')

    a.save()
    quiz = asset.config
    for question in quiz['questions']:
        q = Question(
            title=question['q'],
            lang=asset.lang,
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

    logger.info(f'Assessment was sent for user: {str(user_assessment.user.id)}')

    user_assessment.status = 'SENT'
    user_assessment.save()

    return True
