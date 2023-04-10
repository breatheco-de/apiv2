import logging, json, os
from django.dispatch import receiver
# from .models import Asset, AssetAlias, AssetImage
# from .tasks import (async_regenerate_asset_readme)
from breathecode.admissions.signals import student_edu_status_updated

logger = logging.getLogger(__name__)

# @receiver(student_edu_status_updated, sender=CohortUser)
# def post_save_cohort_user(sender, instance, **kwargs):
#     if instance.educational_status == 'GRADUATED':
#         logger.debug('Procesing student graduation')
#         process_student_graduation.delay(instance.cohort.id, instance.user.id)
